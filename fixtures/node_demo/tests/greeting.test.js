"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const { greeting } = require("../src/greeting.js");

test("returns the post-demo Gateway greeting", () => {
  assert.equal(greeting(), "Hello from UPG");
});
