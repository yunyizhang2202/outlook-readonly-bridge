import unittest
from com_attach import attach_active_outlook
from outlook_core import BridgeError

class ComError(Exception):
    def __init__(self, hresult):
        self.hresult = hresult

class TestAttach(unittest.TestCase):
    def test_ok(self):
        obj=object()
        self.assertIs(attach_active_outlook(lambda x: obj, sleep=lambda _: None), obj)
    def test_retry(self):
        n=[0]
        def get(progid):
            n[0]+=1
            if n[0]<3:
                raise ComError(0x800401E3)
            return "ok"
        self.assertEqual(attach_active_outlook(get, sleep=lambda _: None), "ok")
        self.assertEqual(n[0],3)
    def test_persistent_failure(self):
        def get(progid):
            raise ComError(0x800401E3)
        with self.assertRaises(BridgeError) as ctx:
            attach_active_outlook(get, sleep=lambda _: None)
        self.assertIn("0x800401E3",str(ctx.exception))
    def test_other_hresult(self):
        def get(progid):
            raise ComError(0x80070005)
        with self.assertRaises(BridgeError) as ctx:
            attach_active_outlook(get, sleep=lambda _: None)
        self.assertIn("0x80070005",str(ctx.exception))

if __name__=="__main__":
    unittest.main()
