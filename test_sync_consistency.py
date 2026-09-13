"""Deterministic regressions for local edits racing uploads and downloads."""
import copy
import json
import os
import tempfile
import types
import unittest
from unittest.mock import patch

import api_client as api_module
from api_client import APIClient
import version_store as vs
import sync_coordinator as sync


class Response:
    def __init__(self, data, status=200):
        self.data, self.status_code = data, status

    def json(self):
        return copy.deepcopy(self.data)


def schedule(hours=1):
    return {"settings": {"institution_slug": "school"},
            "atamalar": [{"class": "9A", "subject": "Math", "teacher": "Teacher", "duration": 2}],
            "grid_placements": [{"day": 0, "period": p, "subject_name": "Math",
                                 "teacher_name": "Teacher", "class_name": "9A"} for p in range(hours)],
            "_sync_meta": {"revision": 1}, "_version_meta": {"filename": "v001.roz"}}


class SyncConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.patches = [patch.object(vs, "_base_dir", lambda: self.tmp.name),
                        patch.object(sync, "_thread", types.SimpleNamespace(is_alive=lambda: True)),
                        patch.object(sync, "_queue_maintenance", lambda *a: None),
                        patch.object(APIClient, "load_token", lambda self: None)]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        sync._pending.clear()
        vs.invalidate_version_summary()
        self.api = APIClient()
        self.api._request_with_retry = lambda *a, **k: self.fail("Unexpected network call")
        self.api.get_stored_auth_data = lambda: {}
        self.client_patch = patch.object(api_module, "api_client", self.api)
        self.client_patch.start()
        self.addCleanup(self.client_patch.stop)
        self.path = os.path.join(vs._versions_dir("school"), "v001.roz")
        vs._atomic_write_json(self.path, schedule())

    def read(self):
        with open(self.path) as f:
            return json.load(f)

    def test_pending_reset_cannot_be_replaced_by_old_cloud_snapshot(self):
        self.assertTrue(vs.update_version_in_place("school", "v001.roz", schedule(0)))
        self.assertFalse(self.api._write_if_different(self.path, schedule(1)))
        self.assertEqual(self.read()["grid_placements"], [])
        self.assertTrue(sync.is_pending(self.read()))

    def test_acknowledgement_preserves_newer_edit_and_chains_revision(self):
        vs.update_version_in_place("school", "v001.roz", schedule(0))
        sent = []
        def upload(method, url, **kwargs):
            sent.append(copy.deepcopy(kwargs['json']))
            if len(sent) == 1:
                vs.update_version_in_place("school", "v001.roz", schedule(2))
            return Response({"stored": True, "sync_meta": {"revision": len(sent) + 1}})
        self.api._request_with_retry = upload
        self.assertTrue(sync._send_one(self.path, "school", "v001.roz"))
        self.assertTrue(sync.is_pending(self.read()))
        self.assertEqual(len(self.read()["grid_placements"]), 2)
        self.assertEqual(self.read()["_sync_meta"]["revision"], 2)
        self.assertTrue(sync._send_one(self.path, "school", "v001.roz"))
        self.assertEqual(sent[1]["_sync_meta"]["revision"], 2)
        self.assertFalse(sync.is_pending(self.read()))
        self.assertEqual(self.read()["_sync_meta"]["revision"], 3)
        self.assertNotIn(self.path, sync._pending)

    def test_response_started_before_save_is_ignored_even_after_ack(self):
        old_signature = sync.file_signature(self.path)
        vs.update_version_in_place("school", "v001.roz", schedule(0))
        self.api._request_with_retry = lambda *a, **k: Response({"stored": True, "sync_meta": {"revision": 2}})
        sync._send_one(self.path, "school", "v001.roz")
        self.assertFalse(self.api._write_if_different(self.path, schedule(), old_signature))
        self.assertEqual(self.read()["grid_placements"], [])

    def test_burst_is_coalesced_and_snapshots_are_owned(self):
        data = schedule(2)
        for count in (0, 2, 0, 2):
            data = schedule(count)
            vs.update_version_in_place("school", "v001.roz", data)
        data["grid_placements"].clear()
        self.assertEqual(len(sync._pending), 1)
        self.assertEqual(len(self.read()["grid_placements"]), 2)

    def test_failed_upload_survives_restart(self):
        vs.update_version_in_place("school", "v001.roz", schedule(0))
        self.api._request_with_retry = lambda *a, **k: None
        self.assertFalse(sync._send_one(self.path, "school", "v001.roz"))
        sync._pending.clear()
        sync.resume_pending()
        self.assertIn(self.path, sync._pending)
        self.assertEqual(self.read()["grid_placements"], [])

    def test_server_refusal_is_not_an_acknowledgement(self):
        vs.update_version_in_place("school", "v001.roz", schedule(0))
        self.api._request_with_retry = lambda *a, **k: Response({"stored": False, "refused": "wrong_institution"})
        self.assertFalse(sync._send_one(self.path, "school", "v001.roz"))
        self.assertTrue(sync.is_pending(self.read()))

    def test_real_conflict_keeps_exact_local_recovery_copy(self):
        vs.update_version_in_place("school", "v001.roz", schedule(0))
        self.api._request_with_retry = lambda *a, **k: Response({}, status=409)
        self.assertTrue(sync._send_one(self.path, "school", "v001.roz"))
        backups = [f for f in os.listdir(os.path.dirname(self.path)) if '.conflict-' in f]
        self.assertEqual(len(backups), 1)
        with open(os.path.join(os.path.dirname(self.path), backups[0])) as f:
            self.assertEqual(json.load(f)['grid_placements'], [])
        self.assertFalse(sync.is_pending(self.read()))

    def test_old_revision_cannot_replace_acknowledged_edit(self):
        current = schedule(0)
        current['_sync_meta']['revision'] = 5
        vs._atomic_write_json(self.path, current)
        self.assertFalse(self.api._write_if_different(self.path, schedule()))
        self.assertEqual(self.read()['grid_placements'], [])

    def test_noop_save_does_not_write_or_queue(self):
        normalized = schedule()
        normalized["atamalar"] = vs.sanitize_atamalar(normalized["atamalar"])
        vs._atomic_write_json(self.path, normalized)
        original = sync.file_signature(self.path)
        vs.update_version_in_place('school', 'v001.roz', schedule())
        self.assertEqual(sync.file_signature(self.path), original)
        self.assertFalse(sync._pending)

    def test_unchanged_meta_does_not_touch_disk(self):
        directory = os.path.dirname(os.path.dirname(self.path))
        self.assertTrue(self.api._merge_meta(directory, {'name': 'School'}))
        before = sync.file_signature(os.path.join(directory, 'meta.json'))
        self.assertFalse(self.api._merge_meta(directory, {'name': 'School'}))
        self.assertEqual(before, sync.file_signature(os.path.join(directory, 'meta.json')))

    def test_unchanged_index_only_fetches_index_and_keeps_file_stable(self):
        payload = {'school': {'meta': {'name': 'School'}, 'index': [{
            'filename': 'v001.roz', 'key': 'v001_roz', 'hash': vs.compute_data_hash(schedule()),
            'sync_revision': 1, 'folder_id': None, 'note': ''}]}}
        calls = []
        self.api._request_with_retry = lambda method, url, **kw: calls.append(url) or Response(payload)
        self.api._pull_index()
        before = sync.file_signature(self.path)
        self.assertEqual(self.api._pull_index()[2], 0)
        self.assertEqual(sync.file_signature(self.path), before)
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(url.endswith('/index') for url in calls))

    def test_folder_move_flows_from_cloud_after_ack(self):
        local = schedule()
        local['_version_meta']['folder_id'] = 'old'
        vs._atomic_write_json(self.path, local)
        payload = {'school': {'meta': {}, 'index': [{'filename': 'v001.roz', 'key': 'v001_roz',
                   'hash': vs.compute_data_hash(local), 'folder_id': 'new', 'sync_revision': 2}]}}
        self.api._request_with_retry = lambda *a, **kw: Response(payload)
        self.api._pull_index()
        self.assertEqual(self.read()['_version_meta']['folder_id'], 'new')
        self.assertFalse(sync._pending)

    def test_realtime_fetch_downloads_only_named_version(self):
        remote = schedule(2)
        remote['_sync_meta']['revision'] = 2
        calls = []
        self.api._request_with_retry = lambda method, url, **kw: calls.append(url) or Response(remote)
        ok, _, count = self.api.pull_notified_version('school', 'v001_roz')
        self.assertTrue(ok)
        self.assertEqual(count, 1)
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].endswith('/school/v001_roz'))
        self.assertEqual(self.api.sync_generation, 1)
        self.assertEqual(len(self.read()['grid_placements']), 2)

    def test_realtime_notice_does_not_fetch_over_pending_edit(self):
        vs.update_version_in_place('school', 'v001.roz', schedule(0))
        self.api._request_with_retry = lambda *a, **kw: self.fail('Pending edit should not be fetched')
        self.assertEqual(self.api.pull_notified_version('school', 'v001_roz')[2], 0)
        self.assertEqual(self.read()['grid_placements'], [])



if __name__ == '__main__':
    unittest.main()
