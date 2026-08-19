import { describe, it, expect } from "vitest";
import { formatBytes, formatDate, formatDateTime, CASE_TYPES, INDIAN_STATES, LANGUAGES } from "./utils";

describe("utils", () => {
  describe("formatBytes", () => {
    it("formats bytes correctly", () => {
      expect(formatBytes(0)).toBe("0 B");
      expect(formatBytes(512)).toBe("512 B");
      expect(formatBytes(1024)).toBe("1.0 KB");
      expect(formatBytes(1536)).toBe("1.5 KB");
      expect(formatBytes(1024 * 1024)).toBe("1.0 MB");
      expect(formatBytes(1.5 * 1024 * 1024)).toBe("1.5 MB");
    });
  });

  describe("formatDate", () => {
    it("formats ISO date strings to en-IN locale", () => {
      // Note: timezone may affect the exact date, so test that it produces a valid formatted date
      const result1 = formatDate("2026-01-15T10:30:00Z");
      const result2 = formatDate("2026-12-31T23:59:59Z");
      expect(result1).toMatch(/\d{1,2} \w{3} \d{4}/); // e.g., "15 Jan 2026"
      expect(result2).toMatch(/\d{1,2} \w{3} \d{4}/); // e.g., "31 Dec 2026" or "1 Jan 2027"
    });

    it("handles null and undefined", () => {
      expect(formatDate(null)).toBe("—");
      expect(formatDate(undefined)).toBe("—");
    });
  });

  describe("formatDateTime", () => {
    it("formats ISO datetime strings to en-IN locale", () => {
      const result = formatDateTime("2026-01-15T10:30:00Z");
      expect(result).toMatch(/\d{1,2} \w{3}/); // e.g., "15 Jan"
      expect(result).toMatch(/\d{2}:\d{2}/); // time component
    });

    it("handles null and undefined", () => {
      expect(formatDateTime(null)).toBe("—");
      expect(formatDateTime(undefined)).toBe("—");
    });
  });

  describe("CASE_TYPES", () => {
    it("contains all expected case types", () => {
      expect(CASE_TYPES).toHaveLength(9);
      expect(CASE_TYPES.map(c => c.value)).toEqual([
        "PROPERTY", "CIVIL", "CRIMINAL", "COMMERCIAL", "CORPORATE", "FAMILY", "LABOUR", "TAX", "OTHER"
      ]);
    });
  });

  describe("INDIAN_STATES", () => {
    it("contains Indian states", () => {
      expect(INDIAN_STATES.length).toBeGreaterThan(20);
      expect(INDIAN_STATES).toContain("Karnataka");
      expect(INDIAN_STATES).toContain("Maharashtra");
      expect(INDIAN_STATES).toContain("Tamil Nadu");
    });
  });

  describe("LANGUAGES", () => {
    it("contains 13 supported languages", () => {
      expect(LANGUAGES).toHaveLength(13);
      expect(LANGUAGES.map(l => l.code)).toContain("en");
      expect(LANGUAGES.map(l => l.code)).toContain("hi");
      expect(LANGUAGES.map(l => l.code)).toContain("kn");
    });
  });
});