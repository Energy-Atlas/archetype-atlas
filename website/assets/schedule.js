(function () {
  'use strict';
  const assets=new URL('.',document.currentScript.src);
  let plotting;
  function plotly() {
    if (!plotting) plotting=new Promise((resolve,reject)=>{
      const script=document.createElement('script');script.src=new URL('vendor/plotly-cartesian-3.1.0.min.js',assets);
      script.onload=()=>resolve(window.Plotly);script.onerror=()=>reject(new Error('Plot asset unavailable; exact JSON remains accessible.'));
      document.head.append(script);
    });return plotting;
  }
  const node=(tag,value)=>{const n=document.createElement(tag);n.textContent=value;return n;};
  async function start(section) {
    const button=section.querySelector('.schedule-load'),status=section.querySelector('.schedule-status');
    button.disabled=true;status.textContent='Loading verified schedule…';
    try {
      const raw=await AtlasObjects.load(document.querySelector('.object-json'),'raw');
      const s=ScheduleCore.normalize(raw), profiles=ScheduleCore.uniqueDays(s), Plotly=await plotly();
      const year=section.querySelector('.schedule-year'),holidays=section.querySelector('.schedule-holidays'),select=section.querySelector('.schedule-profile');
      section.querySelector('.schedule-controls').hidden=false;
      if(s.type==='annual'){year.value=s.year;year.disabled=true;holidays.disabled=true;}
      select.replaceChildren();
      if(profiles.length<=12){const o=node('option','All '+profiles.length+' unique profiles');o.value='all';select.append(o);}
      profiles.forEach((p,i)=>{const o=node('option','Profile '+(i+1)+' · '+p.labels.slice(0,2).join(', ')+(p.labels.length>2?' …':''));o.value=i;select.append(o);});
      const daily=section.querySelector('.schedule-day-chart'),heatmap=section.querySelector('.schedule-annual-chart');
      const config={responsive:true,displaylogo:false,toImageButtonOptions:{format:'png',filename:'atlas-schedule'}};
      // Chart colours follow the page's theme tokens (design/ui-design-spec.md, section 0.15).
      const css=getComputedStyle(document.body),token=name=>css.getPropertyValue(name).trim();
      const axis={gridcolor:token('--ea-plot-grid'),zerolinecolor:token('--ea-plot-zeroline'),linecolor:token('--ea-plot-grid')};
      const theme={paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',font:{family:'Geist, system-ui, sans-serif',color:token('--ea-plot-font')},
        colorway:[token('--ea-accent'),'#ff7f0e','#2ca02c','#9467bd','#8c564b','#e377c2','#7f7f7f','#bcbd22','#17becf']};
      const layout={...theme,height:370,margin:{t:35,r:30,b:80,l:70},
        xaxis:{...axis,title:{text:'Hour of day'},range:[0,24],dtick:3},yaxis:{...axis,title:{text:s.unit}},legend:{orientation:'h'}};
      function table(values,label) {
        const output=section.querySelector('.schedule-values');output.replaceChildren(node('p',label));
        const t=document.createElement('table'),head=document.createElement('tr');
        ['Hour interval','Value','Unit'].forEach(v=>head.append(node('th',v)));t.append(head);
        values.forEach((v,h)=>{const row=document.createElement('tr');row.append(node('td',h+':00–'+(h+1)+':00'),node('td',v===null?'Unknown':v),node('td',s.unit));t.append(row);});output.append(t);
      }
      async function drawProfiles() {
        const selected=select.value==='all'?profiles: [profiles[Number(select.value)]];
        await Plotly.react(daily,selected.map(p=>({type:'scatter',mode:'lines',name:'Profile '+(profiles.indexOf(p)+1),
          x:Array.from({length:25},(_,h)=>h),y:[...p.values,p.values[23]],line:{shape:'hv'},connectgaps:false,
          hovertemplate:'%{x}:00<br>%{y} '+s.unit+'<extra>%{fullData.name}</extra>'})),layout,config);
        table(selected[0].values,selected[0].labels.join('; '));
      }
      async function calendarView() {
        try {
          const holidayList=holidays.value.split(',').map(v=>v.trim()).filter(Boolean);
          const data=ScheduleCore.annual(s,Number(year.value),holidayList);
          const custom=Array.from({length:24},(_,h)=>data.dates.map((d,i)=>[h+':00–'+(h+1)+':00',data.dayTypes[i],data.ruleIndices[i]===null?(s.type==='annual'?'annual':'Unknown'):data.ruleIndices[i]]));
          await Plotly.react(heatmap,[{type:'heatmap',x:data.dates,y:Array.from({length:24},(_,h)=>h),z:data.z,
            customdata:custom,colorscale:'Viridis',hoverongaps:false,
            ...(s.unit==='1'?{zmin:0,zmax:1}:{}),colorbar:{title:{text:s.unit}},
            hovertemplate:'%{x}<br>%{customdata[0]}<br>%{z} '+s.unit+'<br>%{customdata[1]} · rule %{customdata[2]}<extra></extra>'}],
            {...theme,height:420,margin:{t:20,r:60,b:65,l:65},xaxis:{...axis,title:{text:'Calendar date'}},yaxis:{...axis,title:{text:'Hour of day'},dtick:3,autorange:'reversed'}},config);
          heatmap.removeAllListeners('plotly_click');
          heatmap.on('plotly_click',async event=>{
            const i=data.dates.indexOf(String(event.points[0].x).slice(0,10));if(i<0)return;
            const values=data.z.map(row=>row[i]);
            await Plotly.react(daily,[{type:'scatter',mode:'lines',name:data.dates[i],x:Array.from({length:25},(_,h)=>h),y:[...values,values[23]],line:{shape:'hv'},connectgaps:false}],layout,config);
            table(values,data.dates[i]+' · '+data.dayTypes[i]+' · '+(data.ruleIndices[i]===null?'annual/unknown':'source rule '+data.ruleIndices[i]));
          });
          status.textContent=profiles.length+' unique day profiles · '+data.dates.length+' days · '+data.missingHours+' unknown hours. '+
            (s.type==='annual'?'Recorded '+s.year+' realization; calendar and overrides are fixed.':'Explicit '+year.value+' preview; '+holidayList.length+' holiday overrides. Design days are listed separately among the profiles.');
        }catch(error){status.textContent=error.message+' Previous valid plots remain visible.';}
      }
      select.addEventListener('change',()=>drawProfiles().catch(e=>{status.textContent=e.message;}));
      section.querySelector('.schedule-update').addEventListener('click',calendarView);
      await drawProfiles();await calendarView();button.hidden=true;
    }catch(error){status.textContent=error.message;button.disabled=false;}
  }
  function init(){document.querySelectorAll('.schedule-viewer').forEach(s=>s.querySelector('.schedule-load').addEventListener('click',()=>start(s)));}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
