import sys,unittest,tempfile,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from extract48v2 import command,WR,THREADS
TOOL=WR/'round47_sis_acquisition/tools/executable/zpaq'

class Tests(unittest.TestCase):
    def test_four_thread_exact_target_no_overwrite(self):
        self.assertEqual(THREADS,4)
        with tempfile.TemporaryDirectory(prefix='zpaq_fixture48v2_') as temp:
            root=Path(temp);src=root/'source';src.mkdir();(src/'chosen.txt').write_bytes(b'known fixture v2\n');(src/'ignored.txt').write_bytes(b'not extracted\n');archive=root/'sample.zpaq'
            subprocess.run([str(TOOL),'add',str(archive),'chosen.txt','ignored.txt','-method','1','-threads','1'],cwd=src,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=30)
            out=root/'destination';out.mkdir();target=out/'chosen-renamed.txt';cmd=command(TOOL,archive,'chosen.txt',target)
            self.assertNotIn('-force',cmd)
            subprocess.run(cmd,cwd=root,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=30)
            self.assertEqual(list(out.iterdir()),[target]);self.assertEqual(target.read_bytes(),b'known fixture v2\n')
            target.write_bytes(b'keep existing')
            subprocess.run(cmd,cwd=root,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
            self.assertEqual(target.read_bytes(),b'keep existing')

if __name__=='__main__':unittest.main()
