// Copyright 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "core/editing/Editor.h"

#include "core/dom/Document.h"
#include "core/editing/testing/EditingTestBase.h"
#include "core/html/HTMLBodyElement.h"
#include "core/html/HTMLDivElement.h"
#include "core/html/HTMLHeadElement.h"
#include "core/html/HTMLHtmlElement.h"
#include "core/html/forms/HTMLInputElement.h"

namespace blink {

class EditorTest : public EditingTestBase {
 protected:
  void MakeDocumentEmpty();
};

void EditorTest::MakeDocumentEmpty() {
  while (GetDocument().firstChild())
    GetDocument().RemoveChild(GetDocument().firstChild());
}

TEST_F(EditorTest, tidyUpHTMLStructureFromBody) {
  Element* body = HTMLBodyElement::Create(GetDocument());
  MakeDocumentEmpty();
  GetDocument().setDesignMode("on");
  GetDocument().AppendChild(body);
  Editor::TidyUpHTMLStructure(GetDocument());

  EXPECT_TRUE(IsHTMLHtmlElement(GetDocument().documentElement()));
  EXPECT_EQ(body, GetDocument().body());
  EXPECT_EQ(GetDocument().documentElement(), body->parentNode());
}

TEST_F(EditorTest, tidyUpHTMLStructureFromDiv) {
  Element* div = HTMLDivElement::Create(GetDocument());
  MakeDocumentEmpty();
  GetDocument().setDesignMode("on");
  GetDocument().AppendChild(div);
  Editor::TidyUpHTMLStructure(GetDocument());

  EXPECT_TRUE(IsHTMLHtmlElement(GetDocument().documentElement()));
  EXPECT_TRUE(IsHTMLBodyElement(GetDocument().body()));
  EXPECT_EQ(GetDocument().body(), div->parentNode());
}

TEST_F(EditorTest, tidyUpHTMLStructureFromHead) {
  Element* head = HTMLHeadElement::Create(GetDocument());
  MakeDocumentEmpty();
  GetDocument().setDesignMode("on");
  GetDocument().AppendChild(head);
  Editor::TidyUpHTMLStructure(GetDocument());

  EXPECT_TRUE(IsHTMLHtmlElement(GetDocument().documentElement()));
  EXPECT_TRUE(IsHTMLBodyElement(GetDocument().body()));
  EXPECT_EQ(GetDocument().documentElement(), head->parentNode());
}

TEST_F(EditorTest, copyGeneratedPassword) {
  // Checks that if the password field has the value generated by Chrome
  // (HTMLInputElement::shouldRevealPassword will be true), copying the field
  // should be available.
  const char* body_content = "<input type='password' id='password'></input>";
  SetBodyContent(body_content);

  HTMLInputElement& element =
      ToHTMLInputElement(*GetDocument().getElementById("password"));

  const String kPasswordValue = "secret";
  element.focus();
  element.setValue(kPasswordValue);
  element.SetSelectionRange(0, kPasswordValue.length());

  Editor& editor = GetDocument().GetFrame()->GetEditor();
  EXPECT_FALSE(editor.CanCopy());

  element.SetShouldRevealPassword(true);
  EXPECT_TRUE(editor.CanCopy());
}

}  // namespace blink