"""Verify saved run aggregates and manuscript numbers, without experiments.

Default: check the DOCX if present, otherwise literal manuscript-builder text.
Use --manuscript final.pdf to explicitly check the rendered PDF (PyMuPDF needed).
Presence checks are complemented by table-row checks for DOCX. Visual QA remains separate.
"""
import argparse, ast, json, math, re, statistics, sys, zipfile
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET
from _config import ROOT, RESULTS, RUNS

def main():
 ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--manuscript',type=Path)
 a=ap.parse_args(); root=Path(ROOT); result=Path(RESULTS)
 p=a.manuscript or root/'JBHI_Stroke_CT_FINAL.docx'; tables=[]
 if p.exists() and p.suffix.lower()=='.pdf':
  import pymupdf
  with pymupdf.open(p) as pdf: text=' '.join(page.get_text() for page in pdf)
 elif p.exists() and p.suffix.lower()=='.docx':
  with zipfile.ZipFile(p) as z: xml=ET.fromstring(z.read('word/document.xml'))
  ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
  text=' '.join(x.text or '' for x in xml.findall('.//w:t',ns))
  tables=[[' '.join(x.text or '' for x in row.findall('.//w:t',ns)) for row in table.findall('w:tr',ns)] for table in xml.findall('.//w:tbl',ns)]
 elif a.manuscript: raise SystemExit('Missing manuscript: '+str(p))
 else:
  p=root/'build_manuscript.py'
  text=' '.join(n.value for n in ast.walk(ast.parse(p.read_text(encoding='utf-8'))) if isinstance(n,ast.Constant) and isinstance(n.value,str))
  print('Checking builder literals; render separately for final-PDF verification.')
 text=re.sub(r'\s+',' ',text); errors=[]; count=0
 def require(label,ok):
  nonlocal count
  count+=1
  if not ok: errors.append(label)
 def ck(label,v,fmt='.4f',scope=text):
  token=format(v,fmt) if isinstance(v,(float,int)) else str(v)
  require(label+' = '+token,re.search(r'(?<!\d)'+re.escape(token)+r'(?!\d)',scope) is not None)
 def read(name): return json.loads((result/name).read_text())
 summ=read('summary.json'); stats=read('stats.json'); att=read('attrib_multiseed.json')
 groups=defaultdict(list)
 for f in Path(RUNS).glob('*.json'):
  r=json.loads(f.read_text()); groups['/'.join(map(str,(r['arch'],r['policy'],r['stream'],r['permuted_labels'],bool(r.get('exclude_dcm',False)))))].append(r)
 require('exactly 36 run records',sum(map(len,groups.values()))==36)
 for key,rs in groups.items():
  require(key+' three seeds',sorted(r['seed'] for r in rs)==[0,1,2])
  scope=text
  if tables:
   config=tables[1]
   arch,policy,stream,perm,nod=key.split('/')
   if perm=='True': row=7
   elif nod=='True': row={'full':8,'nonbrain':9,'exterior':10}[stream]
   elif policy=='random': row={'densenet201':13,'resnet18':16}[arch]
   elif arch!='resnet18': row={'densenet201':1,'resnet50':2}[arch]
   else: row={'full':3,'brain':4,'nonbrain':5,'exterior':6}[stream]
   scope=config[row]
  for metric in ('accuracy','macro_f1','macro_auc'):
   values=[r['test'][metric] for r in rs]
   for suffix,value in [('mean',statistics.mean(values)),('sd',statistics.stdev(values))]:
    require(key+'/'+metric+'_'+suffix+' aggregate',math.isclose(summ[key][metric+'_'+suffix],value,abs_tol=1e-12))
    ck(key+'/'+metric+'_'+suffix,value,scope=scope)
 for arch in ('densenet201','resnet18'):
  delta=100*(summ[arch+'/random/full/False/False']['accuracy_mean']-summ[arch+'/grouped/full/False/False']['accuracy_mean'])
  ck(arch+' leakage pp',delta,'.2f')
  for k in ('leaked_acc','clean_acc'): ck(arch+'/'+k,summ['within_run_leakage'][arch][k])
 for arch in ('densenet201','resnet50','resnet18'):
  for v in summ['bootstrap_ci'][arch+'/grouped']['accuracy'][1:]: ck(arch+' CI',v)
 for name,v in stats.items():
  if name.endswith('_acc'):
   ck(name+' delta',v['delta'])
   for x in v['ci']: ck(name+' CI',abs(x))
   if v['p_two_sided']: ck(name+' p',v['p_two_sided'],'.2f')
 for x in stats['exterior_macro_auc']['ci']: ck('exterior AUC CI',x,'.3f')
 for k,v in stats['sensitivity_reliable_mask'].items(): ck('sensitivity '+k,v['acc'])
 for k,v in read('crossstream.json').items():
  ck('crossstream '+k,v['acc'])
  if k in ('brain','nonbrain'): ck('crossstream '+k+' AUC',v['auc'])
 av=att['summary']; require('three attribution seeds',av['seeds']==3)
 for k,field,scale,fmt in [('enrichment','enrichment',1,'.2f'),('CAM lesion','cam_in_lesion',100,'.2f'),('CAM outside','cam_outside_brain',100,'.1f')]:
  vals=[r[field] for r in att['per_seed'].values()]
  for suffix,val in [('mean',statistics.mean(vals)),('sd',statistics.stdev(vals))]:
   require(k+' aggregate '+suffix,math.isclose(av[field+'_'+suffix],val,abs_tol=1e-12)); ck(k+' '+suffix,val*scale,fmt)
 for field in ('n_lesion','n_brain'):
  for r in att['per_seed'].values(): ck(field,r[field],'.0f')
 dup=read('dup_stats.json'); les=read('lesion_validation.json')
 ck('slice count',dup['n_images'],'.0f'); ck('duplicate pair count',dup['calibration']['gt_pairs'],'.0f')
 ck('redundancy images',dup['stats']['6']['images_in_multi_groups'],'.0f')
 ck('redundancy percent',100*dup['stats']['6']['frac_in_multi_groups'],'.1f')
 ck('lesion masks',les['n'],'.0f'); ck('lesion containment',100*les['lesion_inside_brainmask']['mean'],'.1f')
 ck('head containment',les['lesion_inside_headmask']['mean'],'.3f')
 perc=read('perclass.json')
 for stream,rs in perc['per_class'].items():
  scope=tables[3][{'full':1,'brain':2,'nonbrain':3,'exterior':4}[stream]] if tables else text
  for cls in ('hemorrhagic','ischemic','normal'):
   for metric in ('recall','auc'): ck(stream+'/'+cls+'/'+metric,rs[cls][metric],'.3f',scope=scope)
 for k in ('agreement','both_correct','full_right_nonbrain_wrong'):
  ck(k,100*perc['full_vs_nonbrain_agreement'][k],'.1f')
 for cls,v in perc['geometry_by_class'].items():ck('frame geometry '+cls,100*v['frac_square512'],'.1f')
 for cls,v in zip(('hemorrhagic','ischemic','normal'),summ['reference']['class_counts']):ck('class count '+cls,v,'.0f')
 authors='Tanha Asfika Jaman, Iftee Shekh Iftesham, Mst Lovely Akter, and MOSTAFA FARZANA'
 require('exact author order and capitalization',authors in text)
 require('corresponding author','Corresponding author: Tanha Asfika Jaman.' in text)
 require('repository link','https://github.com/asfika-rafique/accuracy-without-anatomy' in text.replace(' ', ''))
 require('no placeholders',not re.search(r'\b(TODO|FIXME|TBD|placeholder)\b',text,re.I))
 for phrase in ('provably never sees','no patient tissue whatsoever','only region that can contain','all brain tissue deleted','single-seed','Originally No'):
  require('no stale wording: '+phrase,phrase not in text)
 print(f'{count-len(errors)}/{count} checks passed: {p}')
 if errors: raise SystemExit('FAIL\n'+'\n'.join(errors))
 print('PASS: numerical consistency. This is not a rerun of training or bootstrap inference.')

if __name__=='__main__': main()
