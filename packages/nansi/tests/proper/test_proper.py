from typing import *
from unittest import TestCase, main

from nansi.proper import Prop, Proper

from test_helpers import *

__DIR__ = get__DIR__(__file__)

class TestProper(TestCase):
    def test_name(self):
        class A(Proper):
            x = Prop(int)

        self.assertEqual(A.x.name, "x")

    def test_owner(self):
        class A(Proper):
            x = Prop(int)

        self.assertIs(A.x.owner, A)

    def test_full_name(self):
        class A(Proper):
            x = Prop(int)

        self.assertEqual(A.x.full_name, f"{__name__}.A.x")

    def test_str(self):
        class A(Proper):
            x = Prop(int)

        self.assertEqual(str(A.x), f"{__name__}.A.x: {int}")

        class B(A):
            y = Prop(int)

        b = B(x=1, y=2)

        self.assertEqual(str(B.x), f"{__name__}.A.x: {int}")
        self.assertEqual(str(B.y), f"{__name__}.B.y: {int}")
        self.assertEqual(B.x.__str__(b), f"{__name__}.B.x: {int}")
        self.assertEqual(B.y.__str__(b), f"{__name__}.B.y: {int}")


if __name__ == '__main__':
    main()
