type TopbarProps = {
  pageTitle: string;
  userName?: string;
  role: "Admin" | "Faculty";
};


export default function Topbar({
  pageTitle,
  userName = "User",
  role,
}: TopbarProps) {

  return (

    <header
      className="
        flex
        h-16
        items-center
        justify-between
        border-b
        border-slate-200
        bg-white
        px-6
      "
    >

      {/* TITLE */}

      <div
        className="
          flex
          items-center
          gap-3
        "
      >

        <div
          className="
            h-8
            w-1
            rounded-full
            bg-[#0F766E]
          "
        />


        <h2
          className="
            text-xl
            font-semibold
            text-slate-900
          "
        >
          {pageTitle}
        </h2>

      </div>


      {/* USER */}

      <div
        className="
          flex
          items-center
          gap-3
        "
      >

        <div
          className="
            text-right
          "
        >

          <p
            className="
              text-sm
              font-medium
              text-slate-900
            "
          >
            {userName}
          </p>


          <p
            className="
              text-xs
              text-slate-500
            "
          >
            {role}
          </p>

        </div>


        <div
          className="
            flex
            h-10
            w-10
            items-center
            justify-center
            rounded-full
            bg-[#CCFBF1]
            font-bold
            text-[#115E59]
            ring-2
            ring-[#0F766E]/20
          "
        >
          {userName
            .charAt(0)
            .toUpperCase()}
        </div>

      </div>

    </header>

  );
}