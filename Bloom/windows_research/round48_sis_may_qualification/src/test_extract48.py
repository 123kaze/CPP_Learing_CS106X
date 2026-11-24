import unittest,tempfile,subprocess,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;TOOL=WR/'round47_sis_acquisition/tools/executable/zpaq'

class Tests(unittest.TestCase):
    def test_exact_file_to_exact_target_without_overwrite(self):
        meta=json.loads((WR/'round47_sis_acquisition/results/tool.json').read_text());self.assertEqual(hashlib.sha256(TOOL.read_bytes()).hexdigest(),meta['binary_sha256'])
        with tempfile.TemporaryDirectory(prefix='zpaq_fixture48_') as tmp:
            base=Path(tmp);src=base/'source';src.mkdir();(src/'chosen.txt').write_bytes(b'known fixture\n');(src/'other.txt').write_bytes(b'not chosen\n')
            archive=base/'fixture.zpaq'
            subprocess.run([str(TOOL),'add',str(archive),'chosen.txt','other.txt','-method','1','-threads','1'],cwd=src,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=20)
            out=base/'output';out.mkdir();target=out/'renamed.txt'
            cmd=[str(TOOL),'extract',str(archive),'chosen.txt','-to',str(target),'-threads','1','-noattributes']
            subprocess.run(cmd,cwd=base,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=20)
            self.assertEqual(list(out.iterdir()),[target]);self.assertEqual(target.read_bytes(),b'known fixture\n')
            target.write_bytes(b'keep existing\n')
            subprocess.run(cmd,cwd=base,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20)
            self.assertEqual(target.read_bytes(),b'keep existing\n')

if __name__=='__main__':unittest.main()
