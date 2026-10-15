"""Create a native Power BI project with a typed import model and report pages."""
import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DEST=ROOT/'powerbi'
REPORT=DEST/'Exposure.Report'
MODEL=DEST/'Exposure.SemanticModel'
BASE='https://developer.microsoft.com/json-schemas/fabric/item/report/definition/'

def save(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,indent=2),encoding='utf-8')

def field(table,column,measure=False):
    return {('Measure' if measure else 'Column'):{'Expression':{'SourceRef':{'Entity':table}},'Property':column}}

def project(table,column,measure=False):
    return {'field':field(table,column,measure),'queryRef':table+'.'+column,'nativeQueryRef':column}

def visual(page,name,kind,x,y,w,h,roles):
    save(REPORT/f'definition/pages/{page}/visuals/{name}/visual.json',{
        '$schema':BASE+'visualContainer/1.0.0/schema.json','name':name,
        'position':{'x':x,'y':y,'width':w,'height':h,'z':0,'tabOrder':0},
        'visual':{'visualType':kind,'drillFilterOtherVisuals':True,
                  'query':{'queryState':{k:{'projections':v} for k,v in roles.items()}}}})

def build():
    tables=[]
    for name,file in [('Properties','properties'),('Exceptions','exceptions'),('Quarantine','quarantine')]:
        with (ROOT/f'outputs/{file}.csv').open(newline='',encoding='utf-8') as f:
            columns=next(csv.reader(f))
        numeric={'latitude','longitude','tiv_usd','year_built','source_row','record_index'}
        columns=[c for c in columns if c!='flag']
        casts=', '.join('{"'+c+'", '+('type number' if c in numeric else 'type text')+'}' for c in columns)
        m=f'''let
    Source = Csv.Document(File.Contents(OutputFolder & "/{file}.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Selected = Table.SelectColumns(Headers, {json.dumps(columns).replace('[','{').replace(']','}')}),
    Typed = Table.TransformColumnTypes(Selected, {{{casts}}}, "en-US")
in Typed'''
        tables.append({'name':name,'columns':[{'name':c,'dataType':'double' if c in numeric else 'string','sourceColumn':c,'summarizeBy':'none'} for c in columns],
            'partitions':[{'name':name,'mode':'import','source':{'type':'m','expression':m.splitlines()}}]})
    measures={'Accepted Properties':'COUNTROWS(Properties)','Total Insured Value':'SUM(Properties[tiv_usd])',
              'MMI VI Plus TIV':'CALCULATE([Total Insured Value], Properties[band] IN {"VI", "VII+"})',
              'Quarantined Rows':'COUNTROWS(Quarantine)','Rule Exceptions':'COUNTROWS(Exceptions)'}
    tables[0]['measures']=[{'name':n,'expression':e,'formatString':'$#,0' if 'Value' in n or 'TIV' in n else '#,0'} for n,e in measures.items()]
    save(MODEL/'definition.pbism',{'version':'1.0','settings':{}})
    save(MODEL/'model.bim',{'name':'PropertyExposure','compatibilityLevel':1606,'model':{'culture':'en-US','defaultPowerBIDataSourceVersion':'powerBI_V3','tables':tables,
        'expressions':[{'name':'OutputFolder','kind':'m','expression':'"'+str(ROOT/'outputs').replace('\\','/')+'" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'}]}})
    save(DEST/'Property_Exposure.pbip',{'version':'1.0','artifacts':[{'report':{'path':'Exposure.Report'}}],'settings':{'enableAutoRecovery':True}})
    save(REPORT/'definition.pbir',{'version':'4.0','datasetReference':{'byPath':{'path':'../Exposure.SemanticModel'}}})
    save(REPORT/'definition/version.json',{'$schema':BASE+'versionMetadata/1.0.0/schema.json','version':'2.0.0'})
    save(REPORT/'definition/report.json',{'$schema':BASE+'report/1.0.0/schema.json','themeCollection':{},'layoutOptimization':'None'})
    pages={'exposure':'Historical scenario · synthetic property exposure','concentrations':'10 km geographic concentrations','quality':'Data quality · global input population'}
    save(REPORT/'definition/pages/pages.json',{'$schema':BASE+'pagesMetadata/1.0.0/schema.json','pageOrder':list(pages),'activePageName':'exposure'})
    for p,title in pages.items():
        save(REPORT/f'definition/pages/{p}/page.json',{'$schema':BASE+'page/1.0.0/schema.json','name':p,'displayName':title,'displayOption':'FitToPage','height':800,'width':1280})
    for i,metric in enumerate(['Accepted Properties','Total Insured Value','MMI VI Plus TIV']):
        visual('exposure','card'+str(i),'card',20+i*420,20,400,130,{'Values':[project('Properties',metric,True)]})
    visual('exposure','city','slicer',20,170,300,100,{'Values':[project('Properties','city')]})
    visual('exposure','occupancy','slicer',350,170,300,100,{'Values':[project('Properties','occupancy')]})
    visual('exposure','bands','clusteredColumnChart',20,290,610,450,{'Category':[project('Properties','band')],'Y':[project('Properties','Total Insured Value',True)]})
    visual('exposure','cities','clusteredBarChart',650,290,610,450,{'Category':[project('Properties','city')],'Y':[project('Properties','Total Insured Value',True)]})
    visual('concentrations','cells','tableEx',20,20,1240,720,{'Values':[project('Properties','cell_id'),project('Properties','Accepted Properties',True),project('Properties','Total Insured Value',True)]})
    visual('quality','quarantined','card',20,20,600,120,{'Values':[project('Properties','Quarantined Rows',True)]})
    visual('quality','exceptions','clusteredBarChart',20,160,600,560,{'Category':[project('Exceptions','rule')],'Y':[project('Properties','Rule Exceptions',True)]})
    visual('quality','register','tableEx',650,160,610,560,{'Values':[project('Quarantine',c) for c in ['source_row','property_id','issues']]})
    print(DEST/'Property_Exposure.pbip')

if __name__=='__main__': build()
