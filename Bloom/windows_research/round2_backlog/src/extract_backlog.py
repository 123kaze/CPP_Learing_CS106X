"""Read-only extraction of the user workbook; task text is data, not authority."""
from pathlib import Path
import sys,json,zipfile,hashlib,xml.etree.ElementTree as E
ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path('E:/Download/QQDown/PassCache全部待办.xlsx')
ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
with zipfile.ZipFile(SOURCE) as z:
    strings=[''.join(t.text or '' for t in si.findall('.//m:t',ns)) for si in E.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',ns)] if 'xl/sharedStrings.xml' in z.namelist() else []
    rel={r.attrib['Id']:r.attrib['Target'] for r in E.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
    sh=E.fromstring(z.read('xl/workbook.xml')).findall('m:sheets/m:sheet',ns)[0]
    target=rel[sh.attrib['{'+ns['r']+'}id']];path=target.lstrip('/') if target.startswith('/') else 'xl/'+target
    tasks=[]
    for row in E.fromstring(z.read(path)).findall('m:sheetData/m:row',ns):
        r=int(row.attrib['r'])
        if not 5<=r<=47:continue
        values={}
        for c in row.findall('m:c',ns):
            if c.attrib.get('t')=='inlineStr':value=''.join(t.text or '' for t in c.findall('.//m:t',ns))
            else:
                val=c.find('m:v',ns);value='' if val is None else val.text or ''
                if c.attrib.get('t')=='s' and value:value=strings[int(value)]
            values[''.join(x for x in c.attrib['r'] if x.isalpha())]=value
        task=dict(zip(['id','category','title','procedure','purpose','priority','dependencies','owner','estimated_days','source_status'],[values.get(chr(65+i),'') for i in range(10)]))
        task['source_row']=r
        task['in_scope']=task['id'][0] in 'FMBERA' or task['id'] in ('O5','O6')
        task['status']='pending' if task['in_scope'] else 'excluded_C' if task['id'].startswith('C') else 'deferred_nonexperimental'
        tasks.append(task)
out=dict(source=str(SOURCE),source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),sheet=sh.attrib['name'],tasks=tasks)
(ROOT/'plan'/'backlog.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(tasks=len(tasks),experiments=sum(t['in_scope'] for t in tasks)),ensure_ascii=False))
