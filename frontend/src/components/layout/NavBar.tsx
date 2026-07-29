import { Bell, UserCircle } from "lucide-react";

export default function Navbar() {
  return (
    <nav className="h-16 bg-slate-900 text-white flex items-center justify-between px-6 shadow-lg border-b border-slate-700">
      {/* Left Section */}
      <div>
        <h1 className="text-2xl font-bold tracking-wide">
          Urban Heat AI
        </h1>
        <p className="text-xs text-gray-400">
          Smart Climate Analytics Platform
        </p>
      </div>

      {/* Right Section */}
      <div className="flex items-center gap-6">

        <button className="relative hover:text-blue-400 transition">
          <Bell size={22} />
          <span className="absolute -top-2 -right-2 w-2 h-2 bg-red-500 rounded-full"></span>
        </button>

        <div className="flex items-center gap-2 cursor-pointer">

          <UserCircle size={34} />

          <div>
            <p className="font-semibold">
              Admin
            </p>

            <p className="text-xs text-gray-400">
              Project Dashboard
            </p>
          </div>

        </div>

      </div>
    </nav>
  );
}