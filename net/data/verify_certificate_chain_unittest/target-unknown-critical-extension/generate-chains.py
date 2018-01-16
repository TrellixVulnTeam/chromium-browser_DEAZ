#!/usr/bin/python
# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Certificate chain where the target certificate contains an unknown X.509v3
extension (OID=1.2.3.4) that is marked as critical."""

import sys
sys.path += ['..']

import common

# Self-signed root certificate.
root = common.create_self_signed_root_certificate('Root')

# Intermediate certificate.
intermediate = common.create_intermediate_certificate('Intermediate', root)

# Target certificate (has unknown critical extension).
target = common.create_end_entity_certificate('Target', intermediate)
target.get_extensions().add_property('1.2.3.4',
                                     'critical,DER:01:02:03:04')

chain = [target, intermediate, root]
common.write_chain(__doc__, chain, 'chain.pem')