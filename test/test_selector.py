# coding: utf-8

import copy
import selectors
import functools
import os
import socket
import unittest

import asynctest


class Selector_TestCase(unittest.TestCase):
    def setUp(self):
        asynctest.selector.FileDescriptor.next_fd = 0


class Test_FileDescriptor(Selector_TestCase):
    def test_is_an_int(self):
        self.assertIsInstance(asynctest.selector.FileDescriptor(), int)

    def test_init_increments_value(self):
        self.assertEqual(0, asynctest.selector.FileDescriptor())
        self.assertEqual(1, asynctest.selector.FileDescriptor())

        self.assertNotEqual(asynctest.selector.FileDescriptor(),
                            asynctest.selector.FileDescriptor())

    def test_init_increments_value_with_fixed_value(self):
        self.assertEqual(5, asynctest.selector.FileDescriptor(5))
        self.assertEqual(6, asynctest.selector.FileDescriptor())


class Test_FileMock(Selector_TestCase):
    def test_fileno_returns_FileDescriptor(self):
        self.assertIsInstance(asynctest.selector.FileMock().fileno(),
                              asynctest.selector.FileDescriptor)


class Test_SocketMock(Selector_TestCase):
    def test_is_socket(self):
        self.assertIsInstance(asynctest.selector.SocketMock(), socket.socket)

def selector_subtest(method):
    @functools.wraps(method)
    def wrapper(self):
        with self.subTest(test='without_selector'):
            method(self, asynctest.selector.TestSelector(), None)

        with self.subTest(test='with_selector'):
            mock = unittest.mock.Mock(selectors.BaseSelector)
            method(self, asynctest.selector.TestSelector(mock), mock)

    return wrapper


class Test_TestSelector(Selector_TestCase):
    @selector_subtest
    def test_register_mock(self, selector, selector_mock):
        mock = asynctest.selector.FileMock()
        key = selector.register(mock, selectors.EVENT_READ, "data")

        self.assertEqual(key, selector.get_map()[mock])

        if selector_mock:
            self.assertFalse(selector_mock.register.called)

    @selector_subtest
    def test_register_fileno(self, selector, selector_mock):
        with open(os.devnull, 'r') as devnull:
            if selector_mock:
                selector_mock.register.return_value = selectors.SelectorKey(
                    devnull, devnull.fileno(), selectors.EVENT_READ, "data"
                )

            key = selector.register(devnull, selectors.EVENT_READ, "data")

            self.assertEqual(key, selector.get_map()[devnull])

            if selector_mock:
                selector_mock.register.assertCalledWith(devnull,
                                                        selectors.EVENT_READ,
                                                        "data")

    @selector_subtest
    def test_unregister_mock(self, selector, selector_mock):
        mock = asynctest.selector.FileMock()
        selector.register(mock, selectors.EVENT_READ, "data")

        selector.unregister(mock)

        self.assertNotIn(mock, selector.get_map())
        self.assertNotIn(mock.fileno(), selector.get_map())

        if selector_mock:
            self.assertFalse(selector_mock.unregister.called)

    @selector_subtest
    def test_unregister_fileno(self, selector, selector_mock):
        with open(os.devnull, 'r') as devnull:
            if selector_mock:
                key = selectors.SelectorKey(devnull, devnull.fileno(),
                                            selectors.EVENT_READ, "data")
                selector_mock.register.return_value = key
                selector_mock.unregister.return_value = key

            selector.register(devnull, selectors.EVENT_READ, "data")

            selector.unregister(devnull)

            self.assertNotIn(devnull, selector.get_map())
            self.assertNotIn(devnull.fileno(), selector.get_map())

    @selector_subtest
    def test_modify_mock(self, selector, selector_mock):
        mock = asynctest.selector.FileMock()

        original_key = selector.register(mock, selectors.EVENT_READ, "data")
        # modify may update the original key, keep a copy
        original_key = copy.copy(original_key)

        RW = selectors.EVENT_READ | selectors.EVENT_WRITE

        key = selector.modify(mock, RW, "data")

        self.assertNotEqual(original_key, key)
        self.assertEqual(key, selector.get_map()[mock])

        if selector_mock:
            selector_mock.modify.assertCalledWith(mock, RW, "data")

    @selector_subtest
    def test_modify_fileno(self, selector, selector_mock):
        with open(os.devnull, 'r') as devnull:
            if selector_mock:
                selector_mock.modify.return_value = selectors.SelectorKey(
                    devnull, devnull.fileno(), selectors.EVENT_READ, "data2"
                )

            original_key = selector.register(devnull, selectors.EVENT_READ, "data")
            # modify may update the original key, keep a copy
            original_key = copy.copy(original_key)

            key = selector.modify(devnull, selectors.EVENT_READ, "data2")

            self.assertNotEqual(original_key, key)
            self.assertEqual(key, selector.get_map()[devnull])

            if selector_mock:
                selector_mock.modify.assertCalledWith(devnull, selectors.EVENT_READ, "data2")

    @selector_subtest
    def test_modify_but_selector_raises(self, selector, selector_mock):
        if not selector_mock:
            return

        exception = RuntimeError()
        selector_mock.modify.side_effect = exception

        with open(os.devnull, 'r') as devnull:
            key = selector.register(devnull, selectors.EVENT_READ, "data")

            with self.assertRaises(type(exception)) as ctx:
                selector.modify(devnull, selectors.EVENT_READ, "data2")

            self.assertIs(exception, ctx.exception)
            self.assertNotIn(devnull, selector.get_map())

    @selector_subtest
    def test_select(self, selector, selector_mock):
        if selector_mock:
            selector_mock.select.return_value = ["ProbeValue"]
            self.assertEqual(["ProbeValue"], selector.select(5))
            selector_mock.select.assertCalledWith(5)
        else:
            self.assertEqual([], selector.select())

    @selector_subtest
    def test_close(self, selector, selector_mock):
        if not selector_mock:
            return

        selector.close()
        selector_mock.close.assertCalledWith()