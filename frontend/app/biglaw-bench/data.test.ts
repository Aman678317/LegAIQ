import { describe, expect, it } from "vitest";
import { CATEGORIES_BY_TRACK, PARTS, TASKS, rubricTotals } from "./data";

const PART_KEYS = Object.keys(PARTS);

describe("biglaw-bench task catalog", () => {
  it("covers all three benchmark parts with at least two tasks each", () => {
    for (const part of PART_KEYS) {
      expect(TASKS.filter((task) => task.part === part).length).toBeGreaterThanOrEqual(2);
    }
  });

  it("has unique task ids and well-formed tasks", () => {
    const ids = new Set(TASKS.map((task) => task.id));
    expect(ids.size).toBe(TASKS.length);
    for (const task of TASKS) {
      expect(task.title).toBeTruthy();
      expect(task.instructions.length).toBeGreaterThan(80);
      expect(task.inputs.length).toBeGreaterThan(0);
      expect(task.minutes).toBeGreaterThan(0);
      expect(task.category).toBeTruthy();
    }
  });

  it("uses rubric ids that are unique within each task", () => {
    for (const task of TASKS) {
      const ids = [...task.rubric.answerQuality, ...task.rubric.sourceReliability].map((item) => item.id);
      expect(new Set(ids).size, task.id).toBe(ids.length);
    }
  });

  it("gives every task both rubric dimensions, positive credit, and penalties", () => {
    for (const task of TASKS) {
      expect(task.rubric.answerQuality.length, task.id).toBeGreaterThan(0);
      expect(task.rubric.sourceReliability.length, task.id).toBeGreaterThan(0);
      const totals = rubricTotals(task.rubric);
      expect(totals.positive, task.id).toBeGreaterThanOrEqual(8);
      expect(totals.penalties, task.id).toBeGreaterThanOrEqual(2);
    }
  });

  it("signs points correctly: credits positive, penalties negative", () => {
    for (const task of TASKS) {
      for (const item of [...task.rubric.answerQuality, ...task.rubric.sourceReliability]) {
        expect(item.criterion.length).toBeGreaterThan(15);
        expect(Number.isInteger(item.points)).toBe(true);
        expect(item.points).not.toBe(0);
      }
    }
  });

  it("lists all 16 official Core categories across the two tracks", () => {
    expect(CATEGORIES_BY_TRACK.transactional.length).toBe(9);
    expect(CATEGORIES_BY_TRACK.litigation.length).toBe(7);
  });

  it("maps every catalog category to the part it belongs to", () => {
    const known = new Set(TASKS.map((task) => task.category));
    const listed = new Set(
      Object.values(CATEGORIES_BY_TRACK).flatMap((entries) => entries.map((entry) => entry.label)),
    );
    for (const category of known) {
      expect(listed, `task category ${category} should appear in the category map`).toContain(category);
    }
  });
});
