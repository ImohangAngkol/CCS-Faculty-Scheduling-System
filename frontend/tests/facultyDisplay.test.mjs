import {test} from 'node:test';
import assert from 'node:assert/strict';
import {facultyKey, formatFacultyName} from '../src/components/schedule/facultyDisplay.ts';

test('metadata codes, integral float codes and legacy labels identify the same faculty', () => {
  for (const value of ['7','7.0','7.00','Faculty 7','Faculty 7.0']) {
    assert.equal(facultyKey(value),'7');
    assert.equal(formatFacultyName(value),'Faculty 7');
  }
  assert.equal(facultyKey('external:eddie-bouy-palad'),'external:eddie-bouy-palad');
  assert.equal(facultyKey('a1746741-97b6-4e55-990e-06a4cc98dd07'),'a1746741-97b6-4e55-990e-06a4cc98dd07');
});

test('external display uses available names and hides internal keys', () => {
  assert.equal(formatFacultyName('external:eddie-bouy-palad'),'Atty. Eddie Bouy Palad · Preassigned Instructor');
  assert.equal(formatFacultyName('external:another','Dr. Example'),'Dr. Example · Preassigned Instructor');
  assert.equal(formatFacultyName('external:another'),'Preassigned Instructor');
  assert.equal(formatFacultyName('7','Private surname'),'Faculty 7');
  assert.equal(formatFacultyName(''),'Unassigned Faculty');
});
