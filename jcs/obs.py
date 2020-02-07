import hashlib
import os
from typing import Optional

import requests


CACHE_DIR='{}/.cache/jcs'.format(os.path.expanduser('~'))


class OBSImage:
    def __init__(self, url: str):
        # local cache
        self._cache_dir = CACHE_DIR
        os.makedirs(self._cache_dir, exist_ok=True)
        # remote image url
        self._url_remote = url
        # local image url (path)
        self._url_local = os.path.join(
            self.cache_dir,
            os.path.basename(self.url_remote))

    @property
    def cache_dir(self):
        return self._cache_dir

    @property
    def url_remote(self) -> str:
        return self._url_remote

    @property
    def url_local(self) -> str:
        return self._url_local

    @property
    def url_remote_sha256(self) -> Optional[str]:
        """download a .sha256 file from the given url"""
        r = requests.get('{}.sha256'.format(self.url_remote), stream=True)
        if r.status_code == 200:
            # FIXME: this contains the whole file, not just the sha
            return r.text
        return None

    @property
    def url_local_sha256(self) -> Optional[str]:
        if os.path.exists(self.url_local):
            sha256 = hashlib.sha256()
            with open(self.url_local, 'rb') as f:
                for block in iter(lambda: f.read(65536), b''):
                    sha256.update(block)
                return sha256.hexdigest()
        return None

    def _do_download(self, response: requests.Response) -> None:
        with open(self.url_local, 'wb') as f:
            print('Download to file {} ...'.format(self.url_local))
            for chunk in response.iter_content(4096):
                f.write(chunk)
            print('Download to file {} done'.format(self.url_local))

    def download(self) -> Optional[str]:
        r = requests.get(self.url_remote, stream=True)
        if r.status_code != 200:
            raise Exception('Can not get {} ({})'.format(
                self.url_remote, r.status_code))

        if os.path.exists(self.url_local):
            if self.url_remote_sha256 and \
               self.url_local_sha256 in self.url_remote_sha256:
                print('Skipping download. image with sha256 {} '
                      'already local available at {}'.format(
                          self.url_local_sha256, self.url_local))
            else:
                print('Outdated image exist local at {} with '
                      'sha256 {}'.format(self.url_local,
                                         self.url_local_sha256))
                self._do_download(r)
        else:
            self._do_download(r)
        return self.url_local

