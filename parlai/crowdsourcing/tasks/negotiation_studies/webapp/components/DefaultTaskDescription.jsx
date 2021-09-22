/*
 * Copyright (c) 2017-present, Facebook, Inc.
 * All rights reserved.
 * This source code is licensed under the BSD-style license found in the
 * LICENSE file in the root directory of this source tree. An additional grant
 * of patent rights can be found in the PATENTS file in the same directory.
 */

import React from "react";

//Edit side pane
function NegotiationDefaultTaskDescription({ chatTitle, taskDescriptionHtml, children }) {
  return (
    <div>
      <hr style={{ borderTop: "1px solid #555" }} />
      {children}
    </div>
  );
}

export default NegotiationDefaultTaskDescription;