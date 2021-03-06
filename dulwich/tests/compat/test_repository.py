# test_repo.py -- Git repo compatibility tests
# Copyright (C) 2010 Google, Inc.
#
# Dulwich is dual-licensed under the Apache License, Version 2.0 and the GNU
# General Public License as public by the Free Software Foundation; version 2.0
# or (at your option) any later version. You can redistribute it and/or
# modify it under the terms of either of these two licenses.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# You should have received a copy of the licenses; if not, see
# <http://www.gnu.org/licenses/> for a copy of the GNU General Public License
# and <http://www.apache.org/licenses/LICENSE-2.0> for a copy of the Apache
# License, Version 2.0.
#

"""Compatibility tests for dulwich repositories."""


from io import BytesIO
from itertools import chain
import os

from dulwich.objects import (
    hex_to_sha,
    )
from dulwich.repo import (
    check_ref_format,
    )

from dulwich.tests.compat.utils import (
    run_git_or_fail,
    CompatTestCase,
    )


class ObjectStoreTestCase(CompatTestCase):
    """Tests for git repository compatibility."""

    def setUp(self):
        super(ObjectStoreTestCase, self).setUp()
        self._repo = self.import_repo('server_new.export')

    def _run_git(self, args):
        return run_git_or_fail(args, cwd=self._repo.path)

    def _parse_refs(self, output):
        refs = {}
        for line in BytesIO(output):
            fields = line.rstrip(b'\n').split(b' ')
            self.assertEqual(3, len(fields))
            refname, type_name, sha = fields
            check_ref_format(refname[5:])
            hex_to_sha(sha)
            refs[refname] = (type_name, sha)
        return refs

    def _parse_objects(self, output):
        return set(s.rstrip(b'\n').split(b' ')[0] for s in BytesIO(output))

    def test_bare(self):
        self.assertTrue(self._repo.bare)
        self.assertFalse(os.path.exists(os.path.join(self._repo.path, '.git')))

    def test_head(self):
        output = self._run_git(['rev-parse', 'HEAD'])
        head_sha = output.rstrip(b'\n')
        hex_to_sha(head_sha)
        self.assertEqual(head_sha, self._repo.refs[b'HEAD'])

    def test_refs(self):
        output = self._run_git(
          ['for-each-ref', '--format=%(refname) %(objecttype) %(objectname)'])
        expected_refs = self._parse_refs(output)

        actual_refs = {}
        for refname, sha in self._repo.refs.as_dict().items():
            if refname == b'HEAD':
                continue  # handled in test_head
            obj = self._repo[sha]
            self.assertEqual(sha, obj.id)
            actual_refs[refname] = (obj.type_name, obj.id)
        self.assertEqual(expected_refs, actual_refs)

    # TODO(dborowitz): peeled ref tests

    def _get_loose_shas(self):
        output = self._run_git(['rev-list', '--all', '--objects', '--unpacked'])
        return self._parse_objects(output)

    def _get_all_shas(self):
        output = self._run_git(['rev-list', '--all', '--objects'])
        return self._parse_objects(output)

    def assertShasMatch(self, expected_shas, actual_shas_iter):
        actual_shas = set()
        for sha in actual_shas_iter:
            obj = self._repo[sha]
            self.assertEqual(sha, obj.id)
            actual_shas.add(sha)
        self.assertEqual(expected_shas, actual_shas)

    def test_loose_objects(self):
        # TODO(dborowitz): This is currently not very useful since fast-imported
        # repos only contained packed objects.
        expected_shas = self._get_loose_shas()
        self.assertShasMatch(expected_shas,
                             self._repo.object_store._iter_loose_objects())

    def test_packed_objects(self):
        expected_shas = self._get_all_shas() - self._get_loose_shas()
        self.assertShasMatch(expected_shas,
                             chain(*self._repo.object_store.packs))

    def test_all_objects(self):
        expected_shas = self._get_all_shas()
        self.assertShasMatch(expected_shas, iter(self._repo.object_store))
