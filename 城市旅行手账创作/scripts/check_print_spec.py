#!/usr/bin/env python3
"""检查确实可量测的输出字段；整页生成不假称相纸/实拍像素精确。"""
import argparse,hashlib,json,re
from pathlib import Path
from PIL import Image

PAGE=(2185,3130)
PAPER={3:(709,1051),4:(898,1205),5:(1051,1500)}

def check_spec(spec):
    assert spec['dpi']==300,'DPI目标必须为300'
    assert tuple(spec['singlePagePx'])==PAGE,'单页目标像素错误'
    assert len(spec['pagePhysicalCm'])==2 and all(abs(a-b)<.01 for a,b in zip(spec['pagePhysicalCm'],(18.5,26.5))),'单页厘米顺序应为宽18.5、高26.5'
    assert spec['productionMode'] in ('whole_image_generation','precise_photo_inset'),'缺少制作模式'
    for p in spec.get('photos',[]):
        cm=p.get('paperPhysicalCm')
        if cm is not None:
            target={3:(6.0,8.9),4:(7.6,10.2),5:(8.9,12.7)}[p['inch']]
            assert tuple(cm) in (target,target[::-1]),'相纸目标厘米不符'
        if spec['productionMode']=='precise_photo_inset':
            size=tuple(p['paperOuterSizePx']);standard=PAPER[p['inch']]
            assert size in (standard,standard[::-1]),'相纸精确外框不符'
            assert re.fullmatch('[0-9a-fA-F]{64}',p['sha256']),'缺源hash'
    if spec['productionMode']=='precise_photo_inset':
        w,h=spec['fullWithCarrierPx'];boxes=[spec['leftPageBox'],spec['rightPageBox']]
        for x1,y1,x2,y2 in boxes:
            assert (x2-x1,y2-y1)==PAGE and 0<=x1<x2<=w and 0<=y1<y2<=h,'单页像素框无效'
        assert boxes[0][2]<=boxes[1][0],'页面重叠'

def check_files(path):
    spec=json.loads(path.read_text());check_spec(spec)
    image=Image.open(path.parent/spec['finalPng']);image.load()
    assert image.size==tuple(spec['fullWithCarrierPx']),'成品像素尺寸错误'
    dpi=image.info.get('dpi',())
    assert len(dpi)==2 and all(abs(v-300)<1 for v in dpi),'PNG缺300dpi元数据'
    for p in spec.get('photos',[]):
        source=Path(p['file'])
        if not source.is_absolute():source=path.parent/source
        assert source.is_file(),'参考照片不存在'
        with Image.open(source) as im:im.load()
        if spec['productionMode']=='precise_photo_inset':
            assert hashlib.sha256(source.read_bytes()).hexdigest()==p['sha256'],'源照片hash改变'
    if spec.get('printPdf'):
        pdf=(path.parent/spec['printPdf']).read_bytes()
        assert pdf.startswith(b'%PDF-'),'无效PDF'
        boxes=re.findall(rb'/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\]',pdf)
        assert len(boxes)==2,'不能确认PDF两页MediaBox'
        for box in boxes:
            x1,y1,x2,y2=map(float,box)
            assert abs(x2-x1-PAGE[0]*72/300)<.3 and abs(y2-y1-PAGE[1]*72/300)<.3,'PDF页尺寸错误'
    print('整图尺寸、DPI、已声明的来源与可选PDF通过；整页生成的照片像素和相纸实测尺寸未获此脚本认证。')

def self_test():
    base=dict(dpi=300,singlePagePx=list(PAGE),pagePhysicalCm=[18.5,26.5],fullWithCarrierPx=[4920,3530],productionMode='whole_image_generation',photos=[dict(inch=3,paperPhysicalCm=[6,8.9])])
    check_spec(base)
    base['photos'][0]['paperPhysicalCm']=[5.08,7.62]
    try:check_spec(base)
    except AssertionError:pass
    else:raise AssertionError('必须拒绝旧3寸口径')
    base.update(productionMode='precise_photo_inset',leftPageBox=[200,200,2385,3330],rightPageBox=[2535,200,4720,3330],photos=[dict(inch=4,paperPhysicalCm=[7.6,10.2],paperOuterSizePx=[898,1205],sha256='0'*64)])
    check_spec(base)
    base['photos'][0]['paperOuterSizePx']=[900,1200]
    try:check_spec(base)
    except AssertionError:pass
    else:raise AssertionError('必须拒绝旧4寸口径')
    print('自测通过：整页生成目标、精确嵌图目标与旧尺寸拒绝。')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('manifest',nargs='?',type=Path);parser.add_argument('--self-test',action='store_true');args=parser.parse_args()
    if args.self_test:self_test()
    elif args.manifest:check_files(args.manifest)
    else:parser.error('提供制版记录.json或--self-test')
