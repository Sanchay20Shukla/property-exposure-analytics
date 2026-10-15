"""Reproducible property exposure analysis for one historical ShakeMap scenario."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import folium
import geopandas as gpd
import numpy as np
import pandas as pd
import requests
from shapely.geometry import box

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'data' / 'raw'
OUT = ROOT / 'outputs'
GRID_URL = 'https://earthquake.usgs.gov/product/shakemap/ci38457511/atlas/1594160054783/download/grid.xml'
BANDS = ['Below V', 'V', 'VI', 'VII+']

def fetch_grid(refresh=False):
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / 'ridgecrest_grid.xml'
    if refresh or not path.exists():
        response = requests.get(GRID_URL, timeout=120)
        response.raise_for_status()
        ET.fromstring(response.content)  # Never cache an HTML error page.
        path.write_bytes(response.content)
        (RAW / 'source.json').write_text(json.dumps({
            'url': GRID_URL, 'retrieved_utc': datetime.now(timezone.utc).isoformat(),
            'sha256': hashlib.sha256(response.content).hexdigest(),
            'event': 'ci38457511', 'scenario': '2019-07-06 Ridgecrest M7.1',
            'provider': 'USGS ShakeMap Atlas', 'property_data': 'synthetic, seed 42'
        }, indent=2))
    return path

def hazard_zones(path):
    root = ET.parse(path).getroot()
    ns = {'s': root.tag.split('}')[0].strip('{')}
    fields = [f.attrib['name'] for f in root.findall('s:grid_field', ns)]
    frame = pd.read_csv(io.StringIO(root.find('s:grid_data', ns).text), sep=r'\s+', header=None, names=fields)
    spec = root.find('s:grid_specification', ns).attrib
    dx, dy = float(spec['nominal_lon_spacing']), float(spec['nominal_lat_spacing'])
    coverage = box(float(spec['lon_min'])-dx/2, float(spec['lat_min'])-dy/2,
                   float(spec['lon_max'])+dx/2, float(spec['lat_max'])+dy/2)
    selected = frame[frame.MMI >= 5].copy()
    selected['band'] = np.select([selected.MMI >= 7, selected.MMI >= 6], ['VII+', 'VI'], default='V')
    geom = [box(x-dx/2, y-dy/2, x+dx/2, y+dy/2) for x,y in zip(selected.LON, selected.LAT)]
    cells = gpd.GeoDataFrame(selected[['band']], geometry=geom, crs=4326)
    # Snap to the published grid precision to prevent seams from floating point noise.
    cells.geometry = cells.geometry.set_precision(0.000001)
    zones = cells.dissolve(by='band').reset_index()
    zones.to_file(OUT / 'hazard_zones.geojson', driver='GeoJSON')
    gpd.GeoDataFrame({'name':['ShakeMap coverage']}, geometry=[coverage], crs=4326).to_file(OUT/'coverage.geojson', driver='GeoJSON')
    return zones, coverage

def generate_properties():
    rng = np.random.default_rng(42)
    cities = np.array(['Ridgecrest', 'Los Angeles', 'Bakersfield', 'Lancaster', 'San Bernardino'])
    centers = np.array([[-117.67,35.62],[-118.24,34.05],[-119.02,35.37],[-118.15,34.69],[-117.29,34.11]])
    idx = rng.choice(5, 2500, p=[.3,.25,.15,.15,.15])
    xy = centers[idx] + rng.normal(0, .12, (2500,2))
    df = pd.DataFrame({'property_id':[f'P{i:05}' for i in range(2500)], 'city':cities[idx],
        'longitude':xy[:,0], 'latitude':xy[:,1],
        'occupancy':rng.choice(['Residential','Commercial','Industrial'],2500,p=[.65,.25,.1]),
        'construction':rng.choice(['Wood','Masonry','Concrete'],2500),
        'year_built':rng.integers(1940,2025,2500),
        'tiv_usd':np.round(rng.lognormal(13.4,1,2500),-3)})
    df.loc[0:9,'latitude'] = np.nan
    df.loc[10:19,'longitude'] = 200
    df.loc[20:29,'tiv_usd'] = -100
    df.loc[30:39,'occupancy'] = None
    df.loc[40:44,['longitude','latitude']] = df.loc[40:44,['latitude','longitude']].to_numpy()
    df.loc[45:49,'year_built'] = 2030
    df.loc[50:54,'property_id'] = None
    df.loc[55:59,'latitude'] = 0  # Globally valid, outside portfolio scope.
    conflict = df.iloc[[100]].copy(); conflict['tiv_usd'] *= 2
    df = pd.concat([df,df.iloc[60:80],conflict],ignore_index=True)
    df.to_csv(RAW/'properties.csv',index=False)
    return df

def validate(raw):
    required = ['property_id','city','longitude','latitude','occupancy','construction','year_built','tiv_usd']
    absent = set(required)-set(raw.columns)
    if absent: raise ValueError(f'Missing columns: {sorted(absent)}')
    df = raw.copy().reset_index(drop=True)
    df['source_row'] = np.arange(len(df))+2
    duplicates = df.duplicated(subset=required,keep='first')
    removed = df[duplicates].copy()
    df = df[~duplicates].copy()
    for c in ['longitude','latitude','tiv_usd','year_built']:
        df[c] = pd.to_numeric(df[c],errors='coerce')
    conflicts = df.property_id.notna() & df.property_id.duplicated(keep=False)
    rules = {
        'missing_property_id': df.property_id.isna() | df.property_id.astype(str).str.strip().eq(''),
        'conflicting_property_id': conflicts,
        'invalid_coordinate': ~df.longitude.between(-180,180) | ~df.latitude.between(-90,90),
        'outside_california_study_extent': ~(df.longitude.between(-125,-114) & df.latitude.between(32,42)),
        'invalid_tiv': ~np.isfinite(df.tiv_usd) | df.tiv_usd.le(0),
        'invalid_year': ~df.year_built.between(1800,2026) | df.year_built.mod(1).ne(0),
        'invalid_occupancy': ~df.occupancy.isin(['Residential','Commercial','Industrial']),
        'invalid_construction': ~df.construction.isin(['Wood','Masonry','Concrete']),
        'missing_city': df.city.isna() | df.city.astype(str).str.strip().eq('')}
    flags = pd.DataFrame(rules,index=df.index)
    df['issues'] = flags.apply(lambda r:';'.join(r.index[r]),axis=1)
    rejected = df[df.issues.ne('')].copy()
    accepted = df[df.issues.eq('')].copy()
    exceptions = pd.concat([flags[c][flags[c]].rename('flag').to_frame().assign(rule=c) for c in flags])
    exceptions = exceptions.reset_index(names='record_index').merge(df[['source_row','property_id']],left_on='record_index',right_index=True)
    return accepted, rejected, removed, exceptions

def spatial_analysis(accepted,zones,coverage):
    points = gpd.GeoDataFrame(accepted, geometry=gpd.points_from_xy(accepted.longitude,accepted.latitude),crs=4326)
    joined = gpd.sjoin(points,zones[['band','geometry']],how='left',predicate='intersects')
    # Shared cell edges use the highest intensity, and each property contributes once.
    joined['rank'] = joined.band.map({'V':1,'VI':2,'VII+':3}).fillna(0)
    joined = joined.sort_values('rank',ascending=False).drop_duplicates('property_id').drop(columns=['index_right','rank'])
    covered = joined.geometry.covered_by(coverage)
    joined['band'] = joined.band.fillna('Below V')
    joined.loc[~covered,'band'] = 'Outside ShakeMap'
    projected = joined.to_crs(3310)
    # Fixed 10 km grid, projected California Albers, origin (0,0).
    joined['cell_id'] = (np.floor(projected.geometry.x/10000).astype(int).astype(str)+'_'+np.floor(projected.geometry.y/10000).astype(int).astype(str))
    concentration = joined.groupby('cell_id').agg(properties=('property_id','size'),tiv_usd=('tiv_usd','sum')).reset_index()
    concentration['portfolio_share'] = concentration.tiv_usd/concentration.tiv_usd.sum()
    cells=[]
    for cell in concentration.cell_id:
        x,y=map(int,cell.split('_')); cells.append(box(x*10000,y*10000,(x+1)*10000,(y+1)*10000))
    gpd.GeoDataFrame(concentration,geometry=cells,crs=3310).to_file(OUT/'concentration.gpkg',layer='cells',driver='GPKG')
    joined.to_file(OUT/'properties.geojson',driver='GeoJSON')
    return joined,concentration

def build_map(points,zones):
    m=folium.Map(location=[35,-118],zoom_start=7,tiles='OpenStreetMap')
    colors={'V':'#f7c948','VI':'#f08c35','VII+':'#d64550','Below V':'#287d8e','Outside ShakeMap':'#777777'}
    folium.GeoJson(zones, name='USGS MMI grid zones',style_function=lambda f:{'fillColor':colors[f['properties']['band']], 'color':colors[f['properties']['band']], 'weight':1,'fillOpacity':.22},tooltip=folium.GeoJsonTooltip(fields=['band'])).add_to(m)
    layer=folium.FeatureGroup(name='Synthetic properties')
    for row in points.itertuples():
        folium.CircleMarker([row.latitude,row.longitude],radius=3,color=colors[row.band],weight=0,fill=True,fill_opacity=.65,
            tooltip=f'{row.property_id} | MMI {row.band} | ${row.tiv_usd:,.0f}').add_to(layer)
    layer.add_to(m); folium.LayerControl().add_to(m)
    m.get_root().html.add_child(folium.Element('<div style="position:fixed;bottom:25px;left:20px;background:white;padding:12px;z-index:9999;font:14px Arial">RIDGECREST 2019 · SYNTHETIC PROPERTY PORTFOLIO<br>MMI: teal &lt;V · yellow V · orange VI · red VII+<br>Scenario exposure, not a loss forecast</div>'))
    m.save(OUT/'exposure_map.html')

def run(refresh=False,properties=None):
    OUT.mkdir(exist_ok=True,parents=True)
    grid=fetch_grid(refresh)
    zones,coverage=hazard_zones(grid)
    raw=pd.read_csv(properties) if properties else generate_properties()
    profile=pd.DataFrame({'column':raw.columns,'dtype':[str(raw[c].dtype) for c in raw],
        'missing_rows':[int(raw[c].isna().sum()) for c in raw],
        'distinct_non_null':[int(raw[c].nunique()) for c in raw]})
    profile['missing_share']=profile.missing_rows/len(raw) if len(raw) else 0
    profile.to_csv(OUT/'data_profile.csv',index=False)
    accepted,rejected,duplicates,exceptions=validate(raw)
    if accepted.empty: raise ValueError('No valid properties remain after validation')
    points,concentration=spatial_analysis(accepted,zones,coverage)
    clean=pd.DataFrame(points.drop(columns='geometry')).sort_values('property_id')
    summary=clean.groupby(['city','band','occupancy']).agg(properties=('property_id','size'),tiv_usd=('tiv_usd','sum')).reset_index()
    outputs={'properties':clean,'quarantine':rejected,'duplicates':duplicates,'exceptions':exceptions,'exposure_summary':summary,'concentration':concentration}
    with sqlite3.connect(OUT/'exposure.sqlite') as db:
        for name,frame in outputs.items():
            frame.to_csv(OUT/f'{name}.csv',index=False)
            frame.to_sql(name,db,index=False,if_exists='replace')
        db.executescript((ROOT/'sql'/'views.sql').read_text())
    stats={'raw_rows':len(raw),'duplicate_rows_removed':len(duplicates),'quarantined_rows':len(rejected),'accepted_rows':len(clean),
        'reconciliation_difference':len(raw)-len(duplicates)-len(rejected)-len(clean),
        'accepted_tiv_usd':float(clean.tiv_usd.sum()),'scenario_mmi_vi_plus_tiv_usd':float(clean.loc[clean.band.isin(['VI','VII+']),'tiv_usd'].sum()),
        'rule_counts':exceptions.rule.value_counts().to_dict(),'source_sha256':hashlib.sha256(grid.read_bytes()).hexdigest()}
    (OUT/'validation.json').write_text(json.dumps(stats,indent=2))
    build_map(points,zones)
    report=f'''# Validation and scenario findings

Raw records: {len(raw):,}; exact duplicates removed: {len(duplicates):,}; quarantined: {len(rejected):,}; accepted: {len(clean):,}.
Reconciliation difference: {stats['reconciliation_difference']}.

Accepted total insured value (TIV): ${stats['accepted_tiv_usd']:,.0f}. TIV in historical MMI VI or greater cells: ${stats['scenario_mmi_vi_plus_tiv_usd']:,.0f}.
These are synthetic asset values exposed to one historical event, not expected losses.

## Exceptions and recommendations

{exceptions.rule.value_counts().to_string()}

Require source-system coordinate and positive-value checks. Resolve conflicting property IDs with the data owner; both conflicting records are quarantined.
Recover missing attributes from authoritative property records. Never impute coordinates or insured value for exposure reporting.
Review high-value concentration cells for accumulation limits. A low scenario intensity does not establish low future hazard.
Rule counts overlap: one rejected record can trigger multiple rules. The accepted portfolio excludes entire records failing any rule.
'''
    (OUT/'findings.md').write_text(report)
    print(json.dumps(stats,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--refresh',action='store_true'); parser.add_argument('--properties',type=Path)
    args=parser.parse_args(); run(args.refresh,args.properties)
