from typing import *
from unittest import TestCase, main

from nansi.proper import Improper, prop

from test_helpers import *

__DIR__ = get__DIR__(__file__)

class TestImproper(TestCase):
    def test_mapping(self):
        class A(Improper):
            x = prop(Optional[int])
            y = prop(Optional[int])

        a = A(x=1, y=2, z=3)

        for key in ('x', 'y', 'z'):
            self.assertTrue(key in a)

        for key in ('a', '_x'):
            self.assertFalse(key in a)

        self.assertEqual(
            {**a},
            dict(x=1, y=2, z=3),
        )

    def test_inheritance(self):
        class G0(Improper):
            x = prop(Optional[int])

        class G1(G0):
            y = prop(Optional[int])

        class G2(G1):
            z = prop(Optional[int])

        g2 = G2(x=1, y=2, z=3, w=4)

        self.assertEqual(
            g2.extras(),
            {'w': 4}
        )

if __name__ == '__main__':
    main()
