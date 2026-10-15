from pathlib import Path
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

ROOT=Path(__file__).resolve().parent
st.set_page_config(page_title='Property Exposure Atlas',layout='wide')
st.title('Property Exposure Atlas')
st.caption('Ridgecrest 2019 ShakeMap • synthetic California properties • USD • historical scenario exposure')
if not (ROOT/'outputs/properties.csv').exists():
    st.info('Run python pipeline.py to prepare the data.'); st.stop()
df=pd.read_csv(ROOT/'outputs/properties.csv')
cities=st.sidebar.multiselect('Cities', sorted(df.city.unique()), default=sorted(df.city.unique()))
occupancy=st.sidebar.multiselect('Occupancy',sorted(df.occupancy.unique()),default=sorted(df.occupancy.unique()))
view=df[df.city.isin(cities)&df.occupancy.isin(occupancy)]
a,b,c=st.columns(3)
a.metric('Accepted properties',f'{len(view):,}')
b.metric('Total insured value',f'${view.tiv_usd.sum()/1e6:,.1f}M')
c.metric('Historical MMI VI+ exposure',f'${view.loc[view.band.isin(["VI","VII+"]),"tiv_usd"].sum()/1e6:,.1f}M')
exposure,concentration,quality=st.tabs(['Scenario exposure','Concentrations','Data quality'])
with exposure:
    st.bar_chart(view.groupby('band').tiv_usd.sum(),color='#287d8e')
    st.map(view,latitude='latitude',longitude='longitude')
    st.caption('Map and chart follow sidebar filters. Full portfolio hazard layer map is available below.')
    with st.expander('Full portfolio with hazard zones (unfiltered)'):
        components.html((ROOT/'outputs/exposure_map.html').read_text(encoding='utf-8'),height=620)
    st.dataframe(view,hide_index=True)
    st.download_button('Download filtered exposure',view.to_csv(index=False),'filtered_exposure.csv','text/csv')
with concentration:
    cells=view.groupby('cell_id').agg(properties=('property_id','size'),tiv_usd=('tiv_usd','sum')).sort_values('tiv_usd',ascending=False)
    cells['filtered_portfolio_share']=cells.tiv_usd / cells.tiv_usd.sum() if len(cells) else 0
    st.caption('10 km × 10 km cells in EPSG:3310. Shares use the filtered accepted portfolio.')
    st.dataframe(cells)
with quality:
    st.caption('Quality results refer to all input rows and do not follow portfolio filters.')
    st.json((ROOT/'outputs/validation.json').read_text())
    st.dataframe(pd.read_csv(ROOT/'outputs/quarantine.csv'),hide_index=True)
    st.markdown((ROOT/'outputs/findings.md').read_text())
st.info('MMI describes shaking during one historical event. TIV is asset value, not modeled damage, annual probability, or expected loss. Below V means below the chosen threshold within this ShakeMap coverage.')
