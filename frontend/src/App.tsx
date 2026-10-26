import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "@/components/layout/Layout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AcceptInvite } from "@/pages/AcceptInvite";
import { AuditLog } from "@/pages/AuditLog";
import { Dashboard } from "@/pages/Dashboard";
import { Login } from "@/pages/Login";
import { Members } from "@/pages/Members";
import { MyRequests } from "@/pages/MyRequests";
import { NewRequest } from "@/pages/NewRequest";
import { NotFound } from "@/pages/NotFound";
import { Notifications } from "@/pages/Notifications";
import { PendingForMe } from "@/pages/PendingForMe";
import { PlatformAdmin } from "@/pages/PlatformAdmin";
import { ProjectDetail } from "@/pages/ProjectDetail";
import { Projects } from "@/pages/Projects";
import { Register } from "@/pages/Register";
import { RequestDetail } from "@/pages/RequestDetail";
import { Tasks } from "@/pages/Tasks";
import { Workflows } from "@/pages/Workflows";
import { WorkspacePicker } from "@/pages/WorkspacePicker";

export function App() {
  return (
    <Routes>
      {/* public */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* authenticated, but workspace not required */}
      <Route
        path="/accept-invite"
        element={
          <ProtectedRoute requireOrg={false}>
            <AcceptInvite />
          </ProtectedRoute>
        }
      />
      <Route
        path="/workspaces"
        element={
          <ProtectedRoute requireOrg={false}>
            <WorkspacePicker />
          </ProtectedRoute>
        }
      />

      {/* authenticated app shell (requires an active workspace) */}
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/projects" element={<Projects />} />
        <Route path="/projects/:id" element={<ProjectDetail />} />
        <Route path="/tasks" element={<Tasks />} />
        <Route path="/workflows" element={<Workflows />} />
        <Route path="/requests/new" element={<NewRequest />} />
        <Route path="/requests/mine" element={<MyRequests />} />
        <Route path="/requests/pending" element={<PendingForMe />} />
        <Route path="/requests/:id" element={<RequestDetail />} />
        <Route path="/notifications" element={<Notifications />} />
        <Route path="/admin/members" element={<Members />} />
        <Route path="/admin/audit" element={<AuditLog />} />
        <Route path="/platform" element={<PlatformAdmin />} />
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
