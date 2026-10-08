#!/usr/bin/env python3
"""核验制版尺寸、相纸外框、源图hash与打印PDF页尺寸；不替代照片像素/视觉验收。"""
import argparse, hashlib, json, re
from pathlib import Path
from PIL import Image

PAGE = (2185, 3130)
PAPER = {3: (600, 900), 4: (900, 1200), 5: (1050, 1500)}

def check_spec(spec):
    assert spec['dpi'] == 300, 'DPI必须为300'
    assert tuple(spec['singlePagePx']) == PAGE, '单页像素错误'
    assert len(spec['pagePhysicalCm']) == 2 and all(abs(a-b) < .01 for a,b in zip(spec['pagePhysicalCm'], (18.5,26.5))), '单页物理尺寸错误'
    w,h = spec['fullWithCarrierPx']
    boxes = [spec['leftPageBox'], spec['rightPageBox']]
    for x1,y1,x2,y2 in boxes:
        assert (x2-x1,y2-y1) == PAGE, '页裁切尺寸错误'
        assert 0 <= x1 < x2 <= w and 0 <= y1 < y2 <= h, '页越界'
    assert boxes[0][2] <= boxes[1][0], '页重叠'
    assert spec['photos'], '没有真实选图'
    for photo in spec['photos']:
        size = tuple(photo['paperOuterSizePx'])
        standard = PAPER[photo['inch']]
        assert size in (standard, standard[::-1]), '相纸外框（含白边）不符合寸数'
        assert re.fullmatch('[0-9a-fA-F]{64}',photo['sha256']), '缺少源hash'

def check_files(path):
    spec = json.loads(path.read_text())
    check_spec(spec)
    image = Image.open(path.parent / spec['finalPng'])
    image.load()
    assert image.size == tuple(spec['fullWithCarrierPx']), '成品像素尺寸错误'
    dpi = image.info.get('dpi', ())
    assert len(dpi) == 2 and all(abs(v-300) < 1 for v in dpi), '成品DPI元数据错误'
    for photo in spec['photos']:
        source = Path(photo['file'])
        if not source.is_absolute(): source = path.parent / source
        assert hashlib.sha256(source.read_bytes()).hexdigest() == photo['sha256'], '源照片hash改变'
        with Image.open(source) as source_image: source_image.load()
    pdf = (path.parent / spec['printPdf']).read_bytes()
    assert pdf.startswith(b'%PDF-'), '无效PDF'
    matches = re.findall(rb'/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\]', pdf)
    assert len(matches) == 2, '不能确认两页MediaBox；请用现有PDF工具核验后记录，不推断通过'
    for match in matches:
        x1,y1,x2,y2 = map(float,match)
        assert abs(x2-x1-PAGE[0]*72/300) < .3 and abs(y2-y1-PAGE[1]*72/300) < .3, 'PDF页尺寸错误'
    print('尺寸、相纸外框、源hash、解码、PDF两页MediaBox通过；照片像素与视觉需另验收。')

def self_test():
    spec = {'dpi':300, 'singlePagePx':list(PAGE), 'pagePhysicalCm':[18.5,26.5],
            'fullWithCarrierPx':[4920,3530], 'leftPageBox':[200,200,2385,3330],
            'rightPageBox':[2535,200,4720,3330],
            'photos':[{'inch':5,'paperOuterSizePx':[1050,1500],'sha256':'0'*64}]}
    check_spec(spec)
    spec['photos'][0]['paperOuterSizePx'] = [1110,1640]
    try: check_spec(spec)
    except AssertionError: pass
    else: raise AssertionError('必须拒绝额外扩大的相纸外框')
    spec['photos'][0]['paperOuterSizePx'] = [1500,1050]
    check_spec(spec)
    print('自测通过：标准外框、横向相纸、白边外扩拒绝。')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest', nargs='?', type=Path)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test: self_test()
    elif args.manifest: check_files(args.manifest)
    else: parser.error('提供制版记录.json或--self-test')
