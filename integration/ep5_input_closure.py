"""Declared EP5 engineering payload closure, without CAD imports.

Project Python sources are snapshotted separately. Both modes require the
three actual design configurations. Local mode consumes no engineering
payload archive. Full mode additionally reimports the exact native inputs
below; historical archives outside this list are not implied inputs.
"""

SCHEMA = 'razr-ep5-native-input-closure-v1'

_COMMON = {
    'design/product_routing_ep5.json': 'EP5 route, material assumptions and finite relief research configuration',
    'design/product_geometry.json': 'native baseline identity, cabin dimensions, allocations and OLED trial geometry',
    'design/product_routing_ep4.json': 'fixed original EP4 endpoint dimensions and baseline route contract',
}

_FULL = {
    'engineering/panel-bearing-web-20261015/native-templates.tar.gz':
        '34 current mechanical templates and their embedded native manifest',
    'engineering/pawl-actuation-20261015/geometry-manifest.json':
        'original pawl archive and member byte identities',
    'engineering/pawl-actuation-20261015/native-geometry.tar.gz':
        '13 original pawl-actuation STEP members',
    'engineering/pawl-actuation-20261015/NATIVE_MANIFEST.json':
        'original pawl-actuation member roles, volumes and bounds',
    'engineering/cam-coupling-20261015/geometry-v5-manifest.json':
        'original cam-v5 archive and 19 member byte identities',
    'engineering/cam-coupling-20261015/native-v5-geometry.tar.gz':
        '19 original cam-v5 STEP members, including complete KEY and mother',
    'engineering/cam-coupling-20261015/V5_NATIVE_MANIFEST.json':
        'original cam-v5 source identity, member roles, volumes and bounds',
    'engineering/mounted-mechanism-20261015/geometry-manifest.json':
        '64 original mounted STEP member byte identities',
    'engineering/thin-mechanism-20261015/native-verification.json.gz':
        'original contact-profile parameters driving current stop and spring geometry',
}
MOUNTED_ARCHIVE = 'engineering/mounted-mechanism-20261015/native-geometry.tar.gz'


def native_input_roles(mode, verified_mounted_members=False):
    """Return required repository-relative payload paths mapped to their roles.

    A verified external member set substitutes only the original mounted tar
    container. It never substitutes the mounted manifest or other payloads.
    Missing declared inputs are errors; availability must not select a scope.
    """
    if mode not in ('local', 'full') or type(mode) is not str:
        raise ValueError('EP5 input mode must be local or full')
    if type(verified_mounted_members) is not bool:
        raise ValueError('verified-member mode must be an explicit boolean')
    if mode == 'local':
        if verified_mounted_members:
            raise ValueError('local mode does not consume mounted members')
        return dict(sorted(_COMMON.items()))
    result = {**_COMMON,**_FULL}
    if not verified_mounted_members:
        result[MOUNTED_ARCHIVE] = 'original mounted tar container with exact member bytes'
    return dict(sorted(result.items()))
