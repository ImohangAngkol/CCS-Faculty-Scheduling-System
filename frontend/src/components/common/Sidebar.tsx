import {
  NavLink,
} from "react-router-dom";


type SidebarItem = {
  label: string;
  path: string;
};


type SidebarProps = {
  title: string;
  role: "Admin" | "Faculty";
  items: SidebarItem[];
};


export default function Sidebar({
  title,
  role,
  items,
}: SidebarProps) {

  return (

    <aside
      className="
        min-h-screen
        w-64
        shrink-0
        bg-[#115E59]
        text-white
      "
    >

      {/* =============================================== */}
      {/* BRAND */}
      {/* =============================================== */}

      <div
        className="
          border-b
          border-white/10
          px-6
          py-6
        "
      >

        <div
          className="
            mb-3
            flex
            h-11
            w-11
            items-center
            justify-center
            rounded-xl
            bg-[#EAB308]
            font-bold
            text-[#134E4A]
          "
        >
          CCS
        </div>


        <h1
          className="
            text-base
            font-bold
            leading-snug
            text-white
          "
        >
          {title}
        </h1>


        <p
          className="
            mt-1
            text-sm
            text-teal-100
          "
        >
          BS Information Technology
        </p>


        <div
          className="
            mt-3
            inline-flex
            rounded-full
            bg-white/10
            px-3
            py-1
            text-xs
            font-medium
            text-teal-50
          "
        >
          {role} Portal
        </div>

      </div>


      {/* =============================================== */}
      {/* NAVIGATION */}
      {/* =============================================== */}

      <nav
        className="
          space-y-1
          p-4
        "
      >

        {items.map(
          (item) => (

            <NavLink
              key={item.path}
              to={item.path}

              end={
                item.path ===
                "/admin" ||
                item.path ===
                "/faculty"
              }

              className={
                ({
                  isActive,
                }) =>

                  [
                    "block",
                    "rounded-lg",
                    "px-4",
                    "py-3",
                    "text-sm",
                    "font-medium",
                    "transition",

                    isActive
                      ? [
                          "bg-white",
                          "text-[#115E59]",
                          "shadow-sm",
                        ].join(" ")

                      : [
                          "text-teal-50",
                          "hover:bg-white/10",
                          "hover:text-white",
                        ].join(" "),

                  ].join(" ")
              }
            >

              {item.label}

            </NavLink>

          )
        )}

      </nav>


      {/* =============================================== */}
      {/* BOTTOM BRAND ACCENT */}
      {/* =============================================== */}

      <div
        className="
          mx-4
          mt-5
          border-t
          border-white/10
          pt-5
        "
      >

        <div
          className="
            flex
            items-center
            gap-2
          "
        >

          <span
            className="
              h-2
              w-8
              rounded-full
              bg-[#9D174D]
            "
          />

          <span
            className="
              h-2
              w-8
              rounded-full
              bg-[#EAB308]
            "
          />

        </div>


        <p
          className="
            mt-3
            text-xs
            leading-5
            text-teal-200
          "
        >
          MSU-IIT
          <br />
          College of Computer Studies
        </p>

      </div>

    </aside>

  );
}