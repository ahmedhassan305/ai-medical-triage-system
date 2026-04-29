import { describe, expect, it } from "vitest";

import { parseEgyptianNationalId } from "../src/lib/egyptianNationalId";

describe("parseEgyptianNationalId", () => {
  it("parses date of birth and governorate from a valid ID", () => {
    const parsed = parseEgyptianNationalId("30101010112345");

    expect(parsed).not.toBeNull();
    expect(parsed?.dateOfBirth).toBe("2001-01-01");
    expect(parsed?.governorateCode).toBe("01");
    expect(parsed?.governorate).toBe("Cairo");
  });

  it("returns null for invalid IDs", () => {
    expect(parseEgyptianNationalId("123")).toBeNull();
    expect(parseEgyptianNationalId("30113320112345")).toBeNull();
    expect(parseEgyptianNationalId("30101019912345")).toBeNull();
  });
});
