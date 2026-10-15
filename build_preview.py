"""Build recruiter-visible chart previews for the repository's Working Model page."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import geopandas as gpd

ROOT=Path(__file__).resolve().parent
DEST=ROOT/'docs'/'images'
DEST.mkdir(parents=True,exist_ok=True)
df=pd.read_csv(ROOT/'outputs/properties.csv')
stats=json.loads((ROOT/'outputs/validation.json').read_text())
plt.rcParams.update({'font.family':'DejaVu Sans','axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','axes.labelcolor':'#334155','text.color':'#162b45','figure.facecolor':'#f5f8fc','axes.facecolor':'#f5f8fc','savefig.facecolor':'#f5f8fc'})
plt.rcParams['text.parse_math']=False
colors={'Below V':'#287d8e','V':'#edc44d','VI':'#ef8b36','VII+':'#d64550','Outside ShakeMap':'#888888'}
fig,axes=plt.subplots(2,2,figsize=(15,10))
fig.suptitle('PROPERTY EXPOSURE | WORKING MODEL',fontsize=23,x=.06,ha='left',y=.98)
fig.text(.06,.925,'Ridgecrest 2019 USGS ShakeMap  |  Synthetic California properties  |  Currency: USD',fontsize=11)
bands=df.groupby('band').tiv_usd.sum().reindex(['Below V','V','VI','VII+'],fill_value=0)/1e6
bands.plot.bar(ax=axes[0,0],color=[colors[b] for b in bands.index],rot=0)
axes[0,0].set(title='Insured value by historical shaking band',ylabel='TIV (USD millions)',xlabel='MMI threshold band')
city=df.groupby('city').tiv_usd.sum().sort_values()/1e6
city.plot.barh(ax=axes[0,1],color='#287d8e')
axes[0,1].set(title='Exposure distribution by city',xlabel='TIV (USD millions)',ylabel='')
cells=df.groupby('cell_id').tiv_usd.sum().nlargest(8).sort_values()/1e6
cells.plot.barh(ax=axes[1,0],color='#5275af')
axes[1,0].set(title='Largest 10 km concentration cells',xlabel='TIV (USD millions)',ylabel='EPSG:3310 cell ID')
counts=pd.Series({'Accepted':stats['accepted_rows'],'Quarantined':stats['quarantined_rows'],'Duplicate copies':stats['duplicate_rows_removed']})
axes[1,1].bar(counts.index,counts.values,color=['#287d8e','#d64550','#edc44d'])
for i,v in enumerate(counts): axes[1,1].text(i,v+45,f'{v:,}',ha='center',fontsize=12)
axes[1,1].set(title='Source-row disposition (reconciles to 2,521)',ylabel='Rows',ylim=(0,2800))
fig.text(.06,.025,'2,439 accepted properties  |  $2.718B accepted TIV  |  $739.8M in MMI VI+  |  Reconciliation difference: 0',fontsize=12,weight='bold')
fig.text(.06,.005,'Historical scenario exposure only. Asset values and property locations are synthetic. TIV is not modeled loss.',fontsize=10)
fig.tight_layout(rect=[.04,.055,.98,.9],h_pad=3,w_pad=3)
fig.savefig(DEST/'exposure-overview.png',dpi=150); plt.close(fig)
zones=gpd.read_file(ROOT/'outputs/hazard_zones.geojson')
fig,ax=plt.subplots(figsize=(12,10))
for band in ['V','VI','VII+']:
    zones[zones.band==band].plot(ax=ax,color=colors[band],alpha=.28,edgecolor=colors[band],linewidth=.5)
for band in ['Below V','V','VI','VII+']:
    part=df[df.band==band]
    ax.scatter(part.longitude,part.latitude,s=7,c=colors[band],alpha=.65,label=f'MMI {band} ({len(part):,})')
for city,group in df.groupby('city'):
    ax.annotate(city,(group.longitude.median(),group.latitude.median()),xytext=(7,9),textcoords='offset points',fontsize=10,weight='bold',bbox={'facecolor':'white','alpha':.8,'edgecolor':'none','pad':2})
ax.set(xlim=(-120,-116.5),ylim=(33.5,36.5),xlabel='Longitude (WGS84)',ylabel='Latitude (WGS84)',title='Historical shaking zones and synthetic property locations')
ax.set_aspect(1/0.82); ax.legend(loc='lower left',frameon=True)
fig.text(.08,.025,'USGS Ridgecrest 2019 ShakeMap | Colored polygons: derived MMI grid cells | No basemap or administrative boundaries',fontsize=10)
fig.tight_layout(rect=[0,.04,1,.98]); fig.savefig(DEST/'geospatial-exposure.png',dpi=150); plt.close(fig)
print(DEST)
