import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { VersionBadge } from "./VersionBadge";

describe("VersionBadge", () => {
  it("renders the version string", () => {
    render(<VersionBadge version="0.1.0+r7" />);
    expect(screen.getByTestId("version-badge")).toHaveTextContent("0.1.0+r7");
  });

  it("renders a bare version with no deploy counter", () => {
    render(<VersionBadge version="0.1.0" />);
    expect(screen.getByTestId("version-badge")).toHaveTextContent("0.1.0");
  });
});
