import type { ReactNode } from "react";
import { AccessLevelBadge } from "./AccessLevelBadge";

type Props = {
  plan: string;
  children: ReactNode;
};

export function MembershipGate({ plan, children }: Props) {
  return (
    <div>
      <div className="mb-4">
        <AccessLevelBadge level={plan} />
      </div>
      {children}
    </div>
  );
}
