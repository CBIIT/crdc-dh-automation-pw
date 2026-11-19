# Vendored CRDC Data Hub upload CLI

Copied from `crdc-dh-automation/Tools/crdc-datahub-cli-uploader-src` (Katalon repo), which is a copy of
upstream `CBIIT/crdc-datahub-cli-uploader` (CLI_VERSION 4.3 in `src/common/constants.py`) plus the
`bento-common` module.

Kept only what `src/uploader.py` imports at runtime:

- `src/*.py` and `src/common/*.py`
- `src/bento/common/__init__.py` and `src/bento/common/utils.py` (the only bento-common module used)
- `requirements.txt` and the two READMEs

Left out: `src/unit_test`, the rest of `src/bento` (tests with sample data, other helpers), `.github`,
`.gitmodules`, and the Katalon `tmp/` logs and reports.

Do not edit these files here. To update, copy the new upstream source over them and keep the list above.

Runs only through `crdc_pw.utils.cli_uploader` (needs Python 3.13 or newer and the `cli` extra:
`pip install -e ".[cli]"`). API URL and token come from `config/<profile>.yaml`, never from this folder.
