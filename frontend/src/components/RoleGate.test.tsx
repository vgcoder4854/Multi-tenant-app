import { describe, expect, test } from "vitest";
import { screen } from "@testing-library/react";
import { RoleGate } from "@/components/RoleGate";
import { makeAuth, renderWithProviders } from "@/test/utils";

describe("RoleGate", () => {
  test("shows admin-only content to an org_admin", () => {
    renderWithProviders(
      <RoleGate roles={["org_admin"]}>
        <button>Archive</button>
      </RoleGate>,
      { auth: makeAuth({ role: "org_admin" }) },
    );
    expect(screen.getByRole("button", { name: "Archive" })).toBeInTheDocument();
  });

  test("hides admin-only content from an employee", () => {
    renderWithProviders(
      <RoleGate roles={["org_admin"]}>
        <button>Archive</button>
      </RoleGate>,
      { auth: makeAuth({ role: "employee" }) },
    );
    expect(screen.queryByRole("button", { name: "Archive" })).not.toBeInTheDocument();
  });

  test("renders the fallback when the role is not allowed", () => {
    renderWithProviders(
      <RoleGate roles={["org_admin"]} fallback={<span>Not allowed</span>}>
        <button>Archive</button>
      </RoleGate>,
      { auth: makeAuth({ role: "manager" }) },
    );
    expect(screen.getByText("Not allowed")).toBeInTheDocument();
  });
});
