"""Generate SYNTHETIC demonstration responses offline, never in the UI runtime.
Not a reference backend or recorded January measurements. Reproducible seed-free data.
"""
import json, math, pathlib, datetime as dt
ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'public' / '_fixtures'
OUT.mkdir(parents=True, exist_ok=True)
metadata = json.loads((ROOT / 'scripts' / 'metadata.seed.json').read_text())
def write(name, data): (OUT / (name + '.json')).write_text(json.dumps(data, separators=(',', ':')))
write('metadata', metadata)
STATUSES = ['MATCHED','FORECAST_NOT_YET_PUBLISHED','FORECAST_MISSING','ACTUAL_MISSING','FULLY_MISSING','INVALID_VALUE','AMBIGUOUS_FORECAST','AMBIGUOUS_ACTUAL']
NOW = '2026-02-03T10:00:00Z'
def iso(t): return t.strftime('%Y-%m-%dT%H:%M:%SZ')
def warn(code, message, scope='ANALYSIS', intervals=None, data=None, severity='WARNING'):
    return dict(code=code,severity=severity,scope=scope,message=message,affectedCount=len(intervals or []),affectedIntervals=intervals or [],data=data)
def metrics(intervals):
    errors = [i['error']['signed'] for i in intervals if i['error']]
    n = len(errors)
    return dict(n=n,mae=sum(map(abs,errors))/n if n else None,rmse=math.sqrt(sum(e*e for e in errors)/n) if n else None,bias=sum(errors)/n if n else None,directionCounts=dict(over=sum(e>0 for e in errors),under=sum(e<0 for e in errors),exact=sum(e==0 for e in errors)),signConvention='FORECAST_MINUS_ACTUAL',qualified=n!=len(intervals),unavailableReason=None if n else 'NO_MATCHED_INTERVALS')
def result_meta(intervals, start, end):
    n=sum(i['status']=='MATCHED' for i in intervals)
    sources=[]
    for ds in metadata['datasets']:
        forecast=ds['role']=='FORECAST'
        sources.append(dict(dataset=ds['id'],role=ds['role'],filter=ds['filter'],requestedRange=dict(from_=start,to=end,basis='PUBLISH_TIME' if forecast else 'SETTLEMENT_DATE'),rowsReceived=len(intervals)*3 if forecast else len(intervals),rowsRejected=0,rowsFiltered=0,fetchedAt=NOW,cache='HIT',versions=dict(coveringDay=8,eligible=3,afterCutoff=5) if forecast else None))
        sources[-1]['requestedRange']['from']=sources[-1]['requestedRange'].pop('from_')
        if forecast: sources[-1]['requestedRange'].update({'from':start+'T00:00:00Z','to':iso(dt.datetime.fromisoformat(end)+dt.timedelta(days=1))})
    return dict(contractVersion='1.0.0',algorithmVersion='replay/1.0.0',requestId='synthetic-'+start,generatedAt=NOW,sources=sources,unit=dict(label='MW',actual=metadata['datasets'][0]['unit'],forecast=metadata['datasets'][1]['unit']),resolution=dict(deliveryMinutes=30,forecastMinutes=60),policyIds={k:metadata['policies'][k]['id'] for k in ['selection','mapping','duplicates']},counts=dict(expected=len(intervals),matched=n,excluded=len(intervals)-n,byStatus={s:sum(i['status']==s for i in intervals) for s in STATUSES}),coverage=n/len(intervals))
def day(date, preset, scenario):
    start=dt.datetime.fromisoformat(date); rule=preset['rule']; h,m=map(int,rule['localTime'].split(':'))
    cut=start+dt.timedelta(days=rule['dayOffset'],hours=h,minutes=m)
    pub=cut-dt.timedelta(minutes=90)
    position='AFTER_DELIVERY' if cut>=start+dt.timedelta(days=1) else 'INSIDE_DELIVERY' if cut>start else 'BEFORE_DELIVERY'
    applied=dict(utc=iso(cut),london=cut.isoformat(timespec='seconds')+'+00:00',source='RULE',rule=rule,presetId=preset['id'],position=position)
    intervals=[]
    for j in range(48):
        t=start+dt.timedelta(minutes=j*30); hour=t.replace(minute=0)
        # Synthetic smooth weather profile; an hourly forecast is shared by each pair.
        f=round(6600+2100*math.sin((j//2-5)/4)+1100*math.sin((j//2)/1.6)+400*math.cos(start.day))
        amplitude=4200 if start.day==28 else 500 if start.day==19 else 1450
        err=round(amplitude*(0.8+0.8*math.sin(j/5+start.day)))
        if start.day==5: err=round(1700*math.sin(j/5))
        if start.day==19: err=-abs(err)
        if rule['localTime']=='12:00': err=round(err*.86)
        if rule['dayOffset']==1: err=round(err*.45)
        a=f-err
        status='MATCHED'
        if scenario=='empty' or rule['dayOffset']==-3: status='FORECAST_NOT_YET_PUBLISHED'
        elif (scenario=='partial' or rule['dayOffset']==-2) and j>=44: status='FORECAST_NOT_YET_PUBLISHED'
        elif scenario=='edge' and j<7: status=STATUSES[j+1]
        forecast=dict(generation=f,publishTime=iso(pub),periodStart=iso(hour),periodEnd=iso(hour+dt.timedelta(hours=1)),leadMinutes=int((t-pub).total_seconds()/60),ageAtCutoffMinutes=90)
        actual=dict(generation=a,publishTime=iso(t+dt.timedelta(minutes=30)),conflictingValues=None)
        if status in ['FORECAST_NOT_YET_PUBLISHED','FORECAST_MISSING','FULLY_MISSING','AMBIGUOUS_FORECAST']: forecast=None
        if status in ['ACTUAL_MISSING','FULLY_MISSING']: actual=None
        if status=='INVALID_VALUE': actual['generation']=None
        if status=='AMBIGUOUS_ACTUAL': actual.update(generation=None,conflictingValues=[a,a+500])
        flags=[]
        if forecast and forecast['leadMinutes']<0: flags.append('ISSUED_AFTER_DELIVERY_START')
        if scenario=='edge' and j in [8,9,10]: flags.append(['DUPLICATE_EQUIVALENT_FORECAST','DUPLICATE_EQUIVALENT_ACTUAL','ACTUAL_TIMESTAMP_INCONSISTENT'][j-8])
        intervals.append(dict(settlementPeriod=j+1,startTime=iso(t),endTime=iso(t+dt.timedelta(minutes=30)),status=status,exclusionReason=None if status=='MATCHED' else {'FORECAST_NOT_YET_PUBLISHED':'No forecast covering this hour had been published by the decision time.','AMBIGUOUS_FORECAST':'Conflicting forecast values at the deciding publication; no older fallback.','AMBIGUOUS_ACTUAL':'Conflicting actual values at the deciding publication.'}.get(status,status.replace('_',' ').capitalize()+'.'),forecast=forecast,selection=dict(eligibleCount=0 if forecast is None and status!='AMBIGUOUS_FORECAST' else 3,laterCount=5,earliestLaterPublishTime=iso(cut+dt.timedelta(minutes=25)),conflictingValues=[f,f+300] if status=='AMBIGUOUS_FORECAST' else None),actual=actual,error=dict(signed=err,absolute=abs(err),direction='OVER' if err>0 else 'UNDER' if err<0 else 'EXACT') if status=='MATCHED' else None,flags=flags))
    met=metrics(intervals); state='EMPTY' if not met['n'] else 'COMPLETE' if met['n']==48 else 'PARTIAL'
    warnings=[warn('NEWER_VERSION_AFTER_CUTOFF','A newer forecast was published after the decision time and was not used.','SOURCE',data={'publishTime':iso(cut+dt.timedelta(minutes=25))},severity='INFO')]
    if state!='COMPLETE': warnings.insert(0,warn('NO_MATCHED_INTERVALS' if state=='EMPTY' else 'PARTIAL_COVERAGE',f"{met['n']} of 48 half-hours matched. Metrics describe matched intervals only.",data={'matched':met['n'],'expected':48}))
    if position=='AFTER_DELIVERY': warnings.insert(0,warn('HINDSIGHT_CUTOFF','This decision time is after delivery. This is a hindsight view.',data={'cutoff':iso(cut)}))
    if scenario=='edge':
        for code,message,js in [('DUPLICATE_CONFLICT','Conflicting duplicates were excluded.',[5,6]),('DUPLICATE_EQUIVALENT','Equal-valued duplicate records were collapsed.',[8,9]),('ACTUAL_TIMESTAMP_INCONSISTENT','The source timestamp disagrees with the settlement period.',[10])]: warnings.append(warn(code,message,'INTERVAL',[intervals[j]['startTime'] for j in js],severity='INFO' if code=='DUPLICATE_EQUIVALENT' else 'WARNING'))
    matched=[i for i in intervals if i['error']]
    over=[i for i in matched if i['error']['signed']>0]; under=[i for i in matched if i['error']['signed']<0]
    return dict(resultState=state,query=dict(deliveryDate=date,decisionCutoff=applied,businessTimezone='Europe/London'),metadata=result_meta(intervals,date,date),metrics=met,highlights=dict(largestOver=max(over,key=lambda i:i['error']['signed'])['startTime'] if over else None,largestUnder=min(under,key=lambda i:i['error']['signed'])['startTime'] if under else None,versionsUsed=[iso(pub)] if any(i['forecast'] for i in intervals) else [],earliestCoveringPublishTime=iso(pub) if state!='EMPTY' else iso(cut+dt.timedelta(hours=24)),newerVersionAfterCutoff=iso(cut+dt.timedelta(minutes=25))),intervals=intervals,warnings=sorted(warnings,key=lambda w:(w['severity']!='WARNING',w['code'])))
def summary(days, preset):
    ints=[i for d in days for i in d['intervals']]; met=metrics(ints); n=met['n']
    met.update(overShare=met['directionCounts']['over']/n if n else None,underShare=met['directionCounts']['under']/n if n else None)
    errors=sorted(i['error']['signed'] for i in ints if i['error']); absolute=sorted(map(abs,errors))
    def p(values,q): return values[math.ceil(len(values)*q)-1] if values else None
    bins=[]
    if errors:
        for lo in range(math.floor(min(errors)/500)*500,math.floor(max(errors)/500)*500+500,500): bins.append(dict(lowerEdge=lo,upperEdge=lo+500,count=sum(lo<=e<lo+500 for e in errors)))
    valid=[d for d in days if d['metrics']['n']]; complete=[d for d in days if d['resultState']=='COMPLETE']; featured=[]
    for kind,selected in [('WORST_DAY',max(valid,key=lambda d:d['metrics']['mae']) if valid else None),('BEST_DAY',min(complete,key=lambda d:d['metrics']['mae']) if complete else None),('BIAS_HIDES_ERROR',max(complete,key=lambda d:d['metrics']['mae']-abs(d['metrics']['bias'])) if complete else None)]:
        if selected and (kind!='BIAS_HIDES_ERROR' or selected['metrics']['mae']-abs(selected['metrics']['bias'])>=.5*selected['metrics']['mae']):
            data={k:selected['metrics'][k] for k in ['mae','bias']}
            if kind=='BIAS_HIDES_ERROR': data.update(over=selected['metrics']['directionCounts']['over'],under=selected['metrics']['directionCounts']['under'])
            featured.append(dict(kind=kind,deliveryDate=selected['query']['deliveryDate'],suggestedRule=preset['rule'],data=data))
    meta=result_meta(ints,days[0]['query']['deliveryDate'],days[-1]['query']['deliveryDate']); meta['dayCount']=len(days)
    return dict(resultState='EMPTY' if not n else 'COMPLETE' if n==len(ints) else 'PARTIAL',query=dict(**{'from':days[0]['query']['deliveryDate'],'to':days[-1]['query']['deliveryDate']},rule=preset['rule'],ruleSource='RULE',presetId=preset['id'],businessTimezone='Europe/London'),metadata=meta,metrics=met,distribution=dict(absError=dict(p50=p(absolute,.5),p90=p(absolute,.9),p95=p(absolute,.95)),signedError=dict(p10=p(errors,.1),p90=p(errors,.9)),histogram=dict(binWidth=500,bins=bins)),days=[dict(deliveryDate=d['query']['deliveryDate'],cutoff=d['query']['decisionCutoff'],resultState=d['resultState'],expected=48,matched=d['metrics']['n'],**{k:d['metrics'][k] for k in ['mae','rmse','bias','directionCounts']}) for d in days],featured=featured,sensitivity=dict(onTheHourOnly={k:v for k,v in metrics(ints[::2]).items() if k in ['n','mae','rmse','bias']}),warnings=[] if n==len(ints) else [warn('NO_MATCHED_INTERVALS' if not n else 'PARTIAL_COVERAGE',f'{n} of {len(ints)} half-hours matched. Only matched intervals contribute to metrics.')])
presets=metadata['cutoff']['presets']+[dict(id=None,rule=dict(dayOffset=-3,localTime='09:00'),isDefault=False)]
for preset in presets:
    rule=preset['rule']; key=f"{rule['dayOffset']}_{rule['localTime'].replace(':','')}"
    for scenario in ['complete','partial','empty','edge']:
        days=[]
        for j in range(32):
            date=(dt.date(2026,1,1)+dt.timedelta(days=j)).isoformat(); response=day(date,preset,scenario); days.append(response)
            write(f'day_{date}_{key}_{scenario}',response)
        write(f'summary_{key}_{scenario}',summary(days[1:],preset))
print('Generated synthetic fixture catalogue:', len(list(OUT.glob('*.json'))), 'files')
