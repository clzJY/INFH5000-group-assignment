#!/usr/bin/env python3
"""Stage native MetaUrban tiny + existing pedestrian models entirely offline."""
import argparse,hashlib,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from verify_artifacts import digest,verify

def extract_members(archive,destination,models_only=False):
    destination.mkdir(parents=True,exist_ok=False)
    count=0
    with zipfile.ZipFile(archive) as z:
      for i in z.infolist():
        if i.is_dir() or (models_only and not i.filename.endswith('.gltf')):continue
        target=(destination/i.filename).resolve()
        if not target.is_relative_to(destination.resolve()) or i.flag_bits&1:
            raise ValueError(f'Unsafe/encrypted member: {i.filename}')
        z.extract(i,destination);count+=1
    return count

def main():
    p=argparse.ArgumentParser();p.add_argument('--prepare-pedestrians',action='store_true');a=p.parse_args()
    artifacts=ROOT/'cache/mac_artifacts'
    print('ARTIFACTS_VERIFIED',verify(artifacts),flush=True)
    record=Path((ROOT/'outputs/preparation/current_execution_record.txt').read_text().strip())
    profile=ROOT/'assets/streetscape_tiny_20261102';profile.mkdir(parents=True,exist_ok=True)
    upstream=ROOT/'third_party/metaurban/metaurban'
    ped=artifacts/'downloads/assets_pedestrain.zip'
    ped_receipt=record/'pedestrian_import.json'
    if not ped_receipt.exists():
        count=extract_members(ped,profile/'people',models_only=True)
        ped_receipt.write_text(json.dumps(dict(archive=str(ped),sha256=digest(ped),native_gltf_files=count,
            profile=str(profile),scope='Native glTF meshes and motions only, no bundled videos or helper files'),indent=2)+'\n')
    elif json.loads(ped_receipt.read_text())['sha256']!=digest(ped):raise ValueError('Pedestrian archive changed')
    ped_target=profile/'people/assets_pedestrain';link=upstream/'assets_pedestrain'
    if not link.exists():link.symlink_to(ped_target,target_is_directory=True)
    elif link.resolve()!=ped_target.resolve():raise FileExistsError(link)
    if a.prepare_pedestrians:
        print('NATIVE_PEDESTRIAN_MODELS_READY; TINY_SCENE_PENDING',flush=True);return
    tiny=artifacts/'downloads/assets_tiny.zip'
    if not tiny.is_file():raise SystemExit('STREETSCAPE_ASSET_PENDING: assets_tiny.zip (479067250 bytes); use docs/mac_tiny_asset_prompt.txt')
    if tiny.stat().st_size!=479067250:raise ValueError('Tiny archive size differs from inspected public version')
    receipt=record/'tiny_scene_import.json'
    if not receipt.exists():
        count=extract_members(tiny,profile/'scene')
        receipt.write_text(json.dumps(dict(archive=str(tiny),sha256=digest(tiny),files=count,profile=str(profile)),indent=2)+'\n')
    elif json.loads(receipt.read_text())['sha256']!=digest(tiny):raise ValueError('Tiny archive changed')
    target=profile/'scene/assets';link=upstream/'assets'
    assert (target/'version.txt').is_file()
    if not link.exists():link.symlink_to(target,target_is_directory=True)
    elif link.resolve()!=target.resolve():raise FileExistsError(link)
    final=record/'streetscape_import_receipt.json'
    if not final.exists():final.write_text(json.dumps(dict(profile='tiny_with_native_pedestrians',
        archives={x.name:digest(x) for x in (tiny,ped)},pedestrian_receipt=str(ped_receipt),scene_receipt=str(receipt)),indent=2)+'\n')
    project_receipt=profile/'import_receipt.json'
    if not project_receipt.exists():project_receipt.symlink_to(final)
    print('STREETSCAPE_ASSETS_READY_NO_PASSWORD',flush=True)

if __name__=='__main__':main()
