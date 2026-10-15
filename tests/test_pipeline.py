import json
import sqlite3
import sys
from pathlib import Path
import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline import ROOT, OUT, validate, spatial_analysis

def record(**kwargs):
    r=dict(property_id='A',city='Ridgecrest',longitude=-117.6,latitude=35.6,
           occupancy='Residential',construction='Wood',year_built=2000,tiv_usd=100)
    r.update(kwargs); return r

def test_duplicate_and_conflicting_ids():
    raw=pd.DataFrame([record(),record(),record(tiv_usd=200),record(property_id='B')])
    accepted,rejected,dups,exceptions=validate(raw)
    assert len(dups)==1 and len(rejected)==2
    assert accepted.property_id.tolist()==['B']
    assert set(exceptions.rule)=={'conflicting_property_id'}

@pytest.mark.parametrize('changes,issue',[
    ({'longitude':200},'invalid_coordinate'),({'latitude':None},'invalid_coordinate'),
    ({'longitude':35.6,'latitude':-117.6},'invalid_coordinate'),
    ({'latitude':0},'outside_california_study_extent'),
    ({'tiv_usd':float('inf')},'invalid_tiv'),({'tiv_usd':0},'invalid_tiv'),
    ({'occupancy':None},'invalid_occupancy'),({'property_id':''},'missing_property_id')])
def test_quality_rules(changes,issue):
    accepted,rejected,_,_=validate(pd.DataFrame([record(**changes)]))
    assert accepted.empty and issue in rejected.iloc[0].issues

def test_spatial_boundaries_and_outside_coverage(tmp_path,monkeypatch):
    import pipeline
    monkeypatch.setattr(pipeline,'OUT',tmp_path)
    zones=gpd.GeoDataFrame({'band':['V','VI']},geometry=[box(-118,35,-117.6,36),box(-117.6,35,-117,36)],crs=4326)
    raw=pd.DataFrame([record(),record(property_id='B',longitude=-119),record(property_id='C',longitude=-120)])
    points,cells=spatial_analysis(validate(raw)[0],zones,box(-119.5,34,-116,37))
    bands=points.set_index('property_id').band.to_dict()
    assert bands=={'A':'VI','B':'Below V','C':'Outside ShakeMap'}
    assert len(points)==3 and cells.tiv_usd.sum()==300

def test_artifact_reconciliation():
    stats=json.loads((OUT/'validation.json').read_text())
    assert stats['reconciliation_difference']==0
    assert stats['raw_rows']==stats['accepted_rows']+stats['quarantined_rows']+stats['duplicate_rows_removed']
    with sqlite3.connect(OUT/'exposure.sqlite') as db:
        n,tiv=db.execute('SELECT COUNT(*), SUM(tiv_usd) FROM properties').fetchone()
        assert n==stats['accepted_rows'] and tiv==stats['accepted_tiv_usd']
        assert db.execute('SELECT SUM(tiv_usd) FROM v_hazard_exposure').fetchone()[0]==tiv
    spatial=gpd.read_file(OUT/'properties.geojson')
    assert spatial.property_id.is_unique
    assert spatial.tiv_usd.sum()==stats['accepted_tiv_usd']
