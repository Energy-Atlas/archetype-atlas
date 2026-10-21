"""Browser copies must match both complete ground-enabled Python exports."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from scripts.common import ROOT


class FoundationSiteTests(unittest.TestCase):
    def test_selected_ground_dependency_closure_and_browser_parity(self):
        from scripts import construction_foundation_site as site
        from scripts.construction_foundation_release import pilot_contexts,export_pair
        from scripts.construction_foundation_export import session
        from scripts.construction_site import packet_for
        from scripts.construction_equivalent_site import packet_for as unified_packet,load_equivalents
        source=session().source;equivalents=load_equivalents();rows=[]
        for cid in pilot_contexts().values():
            contexts={cid:source['contexts'][cid]};sid=contexts[cid]['construction_set_id']
            d=packet_for(source,sid,contexts);u=unified_packet(equivalents,sid,contexts)
            self.assertEqual(set(d['foundation']['contexts']),{cid})
            self.assertEqual(d['foundation'],u['foundation'])
            rows.append({'id':cid,'detailed':d,'unified':u,'expected':export_pair(cid)})
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'parity.json';path.write_text(json.dumps(rows),encoding='utf-8')
            code="const assert=require('node:assert/strict'),fs=require('node:fs'),core=require('./website/assets/construction_core.js');for(const r of JSON.parse(fs.readFileSync(process.argv[1]))){assert.deepEqual(core.hydrate(r.detailed,r.id),r.expected[0]);assert.deepEqual(core.hydrateUnified(r.unified,r.id),r.expected[1]);const bad=structuredClone(r.detailed);delete bad.foundation.contexts[r.id];assert.throws(()=>core.hydrate(bad,r.id),/foundation/);}"
            result=subprocess.run(['node','-e',code,str(path)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr[:2000])


if __name__=='__main__':unittest.main()
