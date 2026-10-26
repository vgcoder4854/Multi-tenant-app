import { describe, expect, test } from "vitest";
import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { makeAuth, renderWithProviders } from "@/test/utils";

function renderAt(route: string, auth = makeAuth()) {
  return renderWithProviders(
    <Routes>
      <Route path="/login" element={<div>Login page</div>} />
      <Route path="/workspaces" element={<div>Workspaces page</div>} />
      <Route
        path="/secret"
        element={
          <ProtectedRoute>
            <div>Secret content</div>
          </ProtectedRoute>
        }
      />
    </Routes>,
    { route, auth },
  );
}

describe("ProtectedRoute", () => {
  test("redirects to /login when there is no session", () => {
    renderAt("/secret", makeAuth({ isAuthenticated: false, user: null, role: null }));
    expect(screen.getByText("Login page")).toBeInTheDocument();
  });

  test("redirects to /workspaces when authenticated but no active org", () => {
    renderAt("/secret", makeAuth({ activeOrgId: null, role: null }));
    expect(screen.getByText("Workspaces page")).toBeInTheDocument();
  });

  test("renders children when authenticated with an active org", () => {
    renderAt("/secret");
    expect(screen.getByText("Secret content")).toBeInTheDocument();
  });
});
