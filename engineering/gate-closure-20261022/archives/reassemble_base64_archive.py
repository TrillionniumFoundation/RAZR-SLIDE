#!/usr/bin/env python3
"""Reassemble a committed RAZR base64 archive and validate original bytes."""
from pathlib import Path
import argparse,base64,hashlib,json,os,tempfile
def digest(b):return hashlib.sha256(b).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('manifest',type=Path);ap.add_argument('--output',type=Path);args=ap.parse_args()
 mp=args.manifest.resolve(strict=True);root=mp.parent;m=json.loads(mp.read_text())
 assert m['schema']=='razr-base64-archive-parts-v1' and m['encoding']=='base64' and m['ascii_newline'] is False
 fn=m['reassembled_filename'];assert Path(fn).name==fn and fn not in ('','.','..')
 out=args.output or root/fn;assert not out.exists(),'refuse overwrite'
 assert isinstance(m['ordered_parts'],list) and m['ordered_parts'],'empty archive'
 seen=set();h=hashlib.sha256();total=0;temp=None
 try:
  with tempfile.NamedTemporaryFile(prefix=out.name+'.',suffix='.tmp',dir=out.parent,delete=False) as stream:
   temp=Path(stream.name)
   for r in m['ordered_parts']:
    name=r['path'];assert Path(name).name==name and name not in seen,'unsafe or duplicate part';seen.add(name)
    p=root/name;assert not p.is_symlink() and p.is_file() and p.resolve().parent==root
    e=p.read_bytes();assert len(e)==r['encoded_bytes'] and digest(e)==r['encoded_sha256']
    assert hashlib.sha1(b'blob '+str(len(e)).encode()+b'\0'+e).hexdigest()==r['git_blob_sha1']
    b=base64.b64decode(e,validate=True);assert base64.b64encode(b)==e,'noncanonical base64'
    assert len(b)==r['decoded_bytes'] and digest(b)==r['decoded_sha256']
    stream.write(b);h.update(b);total+=len(b)
  assert total==m['reassembled_bytes'] and h.hexdigest()==m['reassembled_sha256']
  os.link(temp,out);temp.unlink();temp=None
 finally:
  if temp is not None and temp.exists():temp.unlink()
 print(json.dumps({'output':str(out),'bytes':total,'sha256':h.hexdigest(),'verified':True}))
if __name__=='__main__':main()
