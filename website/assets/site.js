/* Progressive enhancement: static tables and field evidence work without JS. */
(function () {
  'use strict';
  const core = window.AtlasCore;
  const ownScript = document.currentScript.src;
  const assetsBase = new URL('.', ownScript);
  const node = (tag, text, props = {}) => {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    Object.assign(el, props);
    return el;
  };
  async function json(url) {
    const response = await fetch(url);
    if (!response.ok) throw new Error('Cannot load ' + url + ' (' + response.status + ')');
    return response.json();
  }
  function recordUrl(indexUrl, recordPath) {
    const marker = '/releases/';
    const u = new URL(indexUrl, location.href);
    const root = new URL(u.pathname.slice(0, u.pathname.indexOf(marker) + 1), u.origin);
    return new URL(recordPath.replace(/\.md$/, '/'), root).href;
  }
  async function catalogue(container) {
    const indexUrl = new URL(container.dataset.index, location.href);
    const data = await json(indexUrl);
    const entries = data.entries;
    const query = document.getElementById('atlas-query');
    const filters = [...container.querySelectorAll('select')];
    const result = document.getElementById('atlas-results');
    const count = document.getElementById('atlas-results-count');
    const prev = document.getElementById('atlas-prev'), next = document.getElementById('atlas-next');
    let page = 0;
    for (const select of filters) {
      const key = select.id.replace('atlas-filter-', '');
      const values = new Set(entries.flatMap(r => [r[key], ...(key === 'building' ? r.referenced_buildings :
        key === 'template' ? r.referenced_templates : []) || []]).filter(Boolean));
      [...values].sort().forEach(v => select.append(node('option', v, {value: v})));
    }
    function state() {
      return {q: query.value, ...Object.fromEntries(filters.map(s => [s.id.replace('atlas-filter-', ''), s.value]))};
    }
    function render(updateUrl = true) {
      const s = state(), found = core.filterEntries(entries, s), size = 40;
      const pages = Math.max(1, Math.ceil(found.length / size));
      page = Math.max(0, Math.min(page, pages - 1));
      count.textContent = found.length + ' matching entries in ' + data.release;
      result.replaceChildren();
      if (!found.length) {
        result.append(node('p', 'No matching entries. Reset a filter or use the category tables below.'));
      } else {
        const table = node('table'), head = node('thead'), body = node('tbody'), tr = node('tr');
        ['Entry', 'Kind / program', 'Vintage / template', 'Climate basis', 'Data status'].forEach(v => tr.append(node('th', v, {scope: 'col'})));
        head.append(tr); table.append(head, body);
        for (const row of found.slice(page * size, (page + 1) * size)) {
          const line = node('tr'), name = node('td'), a = node('a', row.name, {href: recordUrl(indexUrl, row.path)});
          name.append(a);
          line.append(name, node('td', row.kind.replaceAll('_', ' ') + (row.program !== 'Not applicable' ? ' / ' + row.program : '')),
            node('td', row.template + (row.kind === 'residential_archetypes' ? ' · stock ' + row.stock_vintage : '')),
            node('td', row.climate + ' · ' + row.climate_basis), node('td', row.status));
          body.append(line);
        }
        const wrap = node('div', undefined, {className: 'atlas-table'}); wrap.append(table); result.append(wrap);
      }
      document.getElementById('atlas-page').textContent = 'Page ' + (page + 1) + ' of ' + pages;
      prev.disabled = page === 0; next.disabled = page === pages - 1;
      if (updateUrl) {
        const search = core.serializeState(s);
        history.replaceState(null, '', location.pathname + (search ? '?' + search : '') + location.hash);
      }
    }
    function restore() {
      const s = core.normalizeState(entries, core.parseState(location.search));
      query.value = s.q || '';
      filters.forEach(select => {
        const value = s[select.id.replace('atlas-filter-', '')] || '';
        // Preserve an unknown shared URL filter rather than silently removing it.
        if (value && ![...select.options].some(o => o.value === value)) select.append(node('option', value, {value}));
        select.value = value;
      });
      page = 0; render(false);
    }
    let debounce;
    query.addEventListener('input', () => { clearTimeout(debounce); debounce = setTimeout(() => {page = 0; render();}, 100); });
    filters.forEach(select => select.addEventListener('change', () => {page = 0; render();}));
    prev.addEventListener('click', () => {page--; render();});
    next.addEventListener('click', () => {page++; render();});
    document.getElementById('atlas-reset').addEventListener('click', () => {
      query.value = ''; filters.forEach(s => {s.value = '';}); page = 0; render();
    });
    window.addEventListener('popstate', restore); restore();
  }
  let plotlyPromise;
  function plotly() {
    if (!plotlyPromise) plotlyPromise = new Promise((resolve, reject) => {
      const script = node('script', undefined, {src: new URL('vendor/plotly-basic-3.1.0.min.js', assetsBase).href});
      script.onload = () => resolve(window.Plotly);
      script.onerror = () => reject(new Error('Chart asset unavailable; inspect the profile tables below.'));
      document.head.append(script);
    });
    return plotlyPromise;
  }
  function downloadCsv(rows) {
    const content = rows.map(row => row.map(value => '"' + String(value).replaceAll('"', '""') + '"').join(',')).join('\n') + '\n';
    const url = URL.createObjectURL(new Blob([content], {type: 'text/csv;charset=utf-8'}));
    const link = node('a', 'Download CSV', {href: url, download: 'atlas-selected-profiles.csv'});
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  async function explorer(section) {
    const base = new URL(section.dataset.recordsBase.replace(/\/?$/, '/'), location.href);
    const ids = JSON.parse(section.dataset.scheduleIds);
    const schedules = new Map();
    const records = new Map();
    const status = section.querySelector('.atlas-chart-status');
    const day = section.querySelector('.atlas-day'), date = section.querySelector('.atlas-date');
    for (const [role, id] of Object.entries(ids)) {
      if (!records.has(id)) records.set(id, (await json(new URL(id + '.json', base))).record);
      schedules.set(role, {role, record: records.get(id)});
    }
    // Overlay shared records without attaching them to the canonical program.
    const label = node('label', 'Overlay a schedule ');
    const select = node('select'); select.append(node('option', 'Choose a schedule…', {value: ''}));
    label.append(select); section.querySelector('.atlas-controls').append(label);
    const index = await json(new URL('../schedule-index.json', base));
    for (const row of index) select.append(node('option', row.name + ' [' + row.units + ']', {value: row.id}));
    select.addEventListener('change', async () => {
      if (!select.value) return;
      try {
        const packet = await json(new URL(select.value + '.json', base));
        schedules.set(packet.record.id + ':overlay', {role: 'overlay', record: packet.record});
        await render();
      } catch (error) {status.textContent = error.message;}
      select.value = '';
    });
    let revision = 0, csvRows = [];
    async function render() {
      const ticket = ++revision, groups = new Map(), profiles = new Map(), display = section.querySelector('.atlas-profile-table');
      const charts = section.querySelector('.atlas-charts');
      display.replaceChildren(); charts.replaceChildren();
      csvRows = [['release', 'schedule_id', 'name', 'role', 'date', 'day_type', 'hour_start', 'value', 'units', 'winning_rule_index']];
      let missing = 0;
      for (const {role, record} of schedules.values()) {
        try {
          const selected = core.selectProfile(record, day.value, date.value);
          profiles.set(role, selected.values);
          const unit = record.units;
          if (!groups.has(unit)) groups.set(unit, []);
          groups.get(unit).push({role, record, selected});
          const detail = node('details'), summary = node('summary', record.source_name + ' · ' + role + ' · ' + unit);
          detail.append(summary);
          const table = node('table'), heading = node('tr');
          ['Hour start', 'Value', 'Unit'].forEach(v => heading.append(node('th', v, {scope: 'col'})));
          table.append(heading);
          selected.values.forEach((v, h) => {
            const tr = node('tr'); tr.append(node('td', h + ':00'), node('td', v), node('td', unit)); table.append(tr);
            csvRows.push([base.pathname.split('/').filter(Boolean).at(-2), record.id, record.source_name,
              role, date.value, day.value, h, v, unit, selected.ruleIndex]);
          });
          const rules = node('ul');
          selected.matching.forEach(i => {
            const r = record.rules[i];
            rules.append(node('li', 'Rule ' + i + ' · source row ' + r.source_index + ' · ' + r.day_types +
              ' · ' + r.start_date.slice(0, 10) + ' → ' + r.end_date.slice(0, 10) +
              (i === selected.ruleIndex ? ' · SELECTED' : '')));
          });
          const sourceLink = node('a', 'Inspect all seasonal source rules and provenance', {
            href: new URL('../schedules/' + record.id + '/', base).href});
          detail.append(table, rules, sourceLink); display.append(detail);
        } catch (error) {
          missing++; display.append(node('p', record.source_name + ': ' + error.message));
        }
      }
      if (profiles.has('heating_setpoint_schedule_id') && profiles.has('cooling_setpoint_schedule_id')) {
        const diagnostic = core.thermostatDiagnostic(profiles.get('heating_setpoint_schedule_id'), profiles.get('cooling_setpoint_schedule_id'));
        display.prepend(node('p', 'Thermostat minimum deadband: ' + diagnostic.minimumDeadband.toFixed(3) +
          ' C. Heating above cooling at hour starts: ' + (diagnostic.overlapHours.join(', ') || 'none') +
          '. Source values are retained; downstream controls may differ.'));
      }
      status.textContent = schedules.size + ' schedules inspected' + (missing ? '; ' + missing + ' unavailable for this selection' : '');
      try {
        const Plotly = await plotly();
        if (ticket !== revision) return;
        for (const [unit, traces] of groups) {
          if (ticket !== revision) return;
          const chart = node('div', undefined, {className: 'atlas-plot'});
          chart.setAttribute('role', 'img');
          chart.setAttribute('aria-label', 'Daily schedules in ' + unit + '; exact values in the following tables');
          charts.append(chart);
          const palette = ['#16756c', '#bd5b36', '#51739d', '#997a24', '#7b5591', '#467743'];
          await Plotly.newPlot(chart, traces.map(({role, record, selected}, i) => ({
            x: Array.from({length: 25}, (_, h) => h), y: [...selected.values, selected.values[23]],
            type: 'scatter', mode: 'lines', name: record.source_name + ' · ' + role,
            line: {shape: 'hv', width: 2.5, color: palette[i % palette.length]},
            hovertemplate: '%{x}:00<br>%{y} ' + unit + '<extra>%{fullData.name}</extra>',
          })), {
            autosize: true, height: 380, margin: {t: 25, r: 20, b: 110, l: 70},
            paper_bgcolor: '#ffffff', plot_bgcolor: '#ffffff',
            xaxis: {title: {text: 'Hour of day (source profile)'}, range: [0, 24], dtick: 3},
            yaxis: {title: {text: unit}, rangemode: 'normal'},
            legend: {orientation: 'h', y: -0.28}, font: {family: 'system-ui, sans-serif', color: '#253c3a'},
          }, {responsive: true, displaylogo: false, toImageButtonOptions: {format: 'png', filename: 'atlas-schedules'}});
          if (ticket !== revision) return;
        }
      } catch (error) {if (ticket === revision) status.textContent += '. ' + error.message;}
    }
    day.addEventListener('change', () => render().catch(e => {status.textContent = e.message;}));
    date.addEventListener('change', () => render().catch(e => {status.textContent = e.message;}));
    section.querySelector('.atlas-csv').addEventListener('click', () => downloadCsv(csvRows));
    await render();
  }
  async function residentialProfile(section) {
    const profile = await json(new URL(section.dataset.profile, location.href));
    const view = section.querySelector('.atlas-res-view'), date = section.querySelector('.atlas-res-date');
    const columns = section.querySelector('.atlas-res-columns'), status = section.querySelector('.atlas-res-status');
    const charts = section.querySelector('.atlas-res-charts'), table = section.querySelector('.atlas-res-table');
    const fixed = section.dataset.fixed === 'true';
    const allowed = fixed ? new Set(section.dataset.columns.split(',')) : null;
    const defaults = fixed ? allowed : new Set(['occupants', 'lighting_interior', 'heating_setpoint', 'cooling_setpoint']);
    Object.keys(profile.metadata.columns).forEach(column => {
      if (allowed && !allowed.has(column)) return;
      const option = node('option', column + ' (' + profile.metadata.columns[column] + ')', {value: column});
      option.selected = defaults.has(column); columns.append(option);
    });
    let revision = 0;
    async function render() {
      const ticket = ++revision;
      const selected = [...columns.selectedOptions].map(o => o.value);
      const result = core.annualProfile(profile, view.value, date.value, selected);
      date.disabled = view.value === 'annual';
      charts.replaceChildren(); table.replaceChildren();
      status.textContent = result.labels.length + (fixed ? ' fixed hourly intervals; local standard time; source monthly multipliers; no temperature feedback' : ' executed hourly intervals; local standard time; nominal thermostat setpoints; station-proxy weather');
      const summary = node('table'); summary.className = 'atlas-profile-table';
      const head = node('tr'); ['Series', 'Unit', 'Minimum', 'Maximum', 'Mean'].forEach(t => head.append(node('th', t))); summary.append(head);
      for (const trace of result.traces) {
        const row = node('tr'), values = trace.values;
        [trace.column, trace.unit, Math.min(...values).toPrecision(5), Math.max(...values).toPrecision(5),
          (values.reduce((a, b) => a + b, 0) / values.length).toPrecision(5)].forEach(t => row.append(node('td', t)));
        summary.append(row);
      }
      const wrapper = node('div'); wrapper.className = 'atlas-table'; wrapper.append(summary); table.append(wrapper);
      if (!selected.length) {status.textContent = 'Select at least one series; missing end uses remain unresolved.'; return;}
      const Plotly = await plotly();
      if (ticket !== revision) return;
      for (const unit of ['dimensionless', 'degC']) {
        const traces = result.traces.filter(t => t.unit === unit);
        if (!traces.length) continue;
        const chart = node('div', undefined, {className: 'atlas-plot'});
        chart.setAttribute('aria-label', (fixed ? 'Fixed source-default profiles in ' : 'Executed residential profiles in ') + unit);
        charts.append(chart);
        await Plotly.newPlot(chart, traces.map(t => ({x: result.labels, y: t.values, name: t.column, mode: 'lines',
          line: {shape: 'hv'}, hovertemplate: '%{x}<br>%{y} ' + unit + '<extra>' + t.column + '</extra>'})),
          {title: {text: unit === 'degC' ? 'Nominal thermostat profiles (before unavailable-day overrides)' : (fixed ? 'Fixed normalized source defaults' : 'Executed normalized use profiles')},
           xaxis: {title: {text: 'Calendar / local standard time'}, rangeslider: {visible: view.value === 'annual'}},
           yaxis: {title: {text: unit}}, margin: {l: 65, r: 25, t: 65, b: 75},
           legend: {orientation: 'h', y: -0.25}, height: 390}, {responsive: true, displaylogo: false});
        if (ticket !== revision) return;
      }
    }
    const update = () => render().catch(error => {status.textContent = error.message;});
    view.addEventListener('change', update); date.addEventListener('change', update); columns.addEventListener('change', update);
    await render();
  }
  const start = () => {
    const catalog = document.getElementById('atlas-catalogue');
    if (catalog) catalogue(catalog).catch(error => {
      document.getElementById('atlas-results-count').textContent = error.message + '. Use the static category tables below.';
    });
    document.querySelectorAll('.atlas-explorer').forEach(section => explorer(section).catch(error => {
      section.querySelector('.atlas-chart-status').textContent = error.message + '. Inspect source rule tables and downloads below.';
    }));
    document.querySelectorAll('.atlas-residential-profile').forEach(section => residentialProfile(section).catch(error => {
      section.querySelector('.atlas-res-status').textContent = error.message + '. Inspect canonical downloads below.';
    }));
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
