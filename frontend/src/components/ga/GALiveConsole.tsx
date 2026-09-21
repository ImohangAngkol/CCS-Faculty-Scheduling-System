import {
  useEffect,
  useRef,
  useState,
} from "react";


type GALiveConsoleProps = {
  logs: string[];
  loading: boolean;
};


export default function GALiveConsole({
  logs,
  loading,
}: GALiveConsoleProps) {

  const consoleRef =
    useRef<HTMLDivElement | null>(
      null
    );

  const bottomRef =
    useRef<HTMLDivElement | null>(
      null
    );


  const [
    autoScroll,
    setAutoScroll,
  ] = useState(true);


  function handleScroll() {
    const consoleElement =
      consoleRef.current;

    if (!consoleElement) {
      return;
    }

    const distanceFromBottom =
      consoleElement.scrollHeight -
      consoleElement.scrollTop -
      consoleElement.clientHeight;

    setAutoScroll(
      distanceFromBottom < 60
    );
  }


  useEffect(() => {
    if (!autoScroll) {
      return;
    }

    bottomRef.current
      ?.scrollIntoView({
        behavior: "auto",
      });
  }, [
    logs,
    autoScroll,
  ]);


  function jumpToLatest() {
    setAutoScroll(true);

    bottomRef.current
      ?.scrollIntoView({
        behavior: "smooth",
      });
  }


  return (
    <div
      className="
        overflow-hidden
        rounded-xl
        border
        border-[#115E59]
        bg-slate-950
        shadow-sm
      "
    >

      {/* HEADER */}

      <div
        className="
          flex
          items-center
          justify-between
          border-b
          border-slate-800
          bg-[#134E4A]
          px-4
          py-3
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
              h-3
              w-3
              rounded-full
              bg-red-500
            "
          />

          <span
            className="
              h-3
              w-3
              rounded-full
              bg-[#EAB308]
            "
          />

          <span
            className="
              h-3
              w-3
              rounded-full
              bg-teal-400
            "
          />

          <span
            className="
              ml-3
              text-sm
              font-medium
              text-white
            "
          >
            GA Live Progress
          </span>

        </div>


        <div
          className="
            flex
            items-center
            gap-3
          "
        >

          {!autoScroll && (
            <button
              onClick={jumpToLatest}
              className="
                rounded-md
                bg-[#0F766E]
                px-3
                py-1
                text-xs
                font-semibold
                text-white
                transition
                hover:bg-[#115E59]
              "
            >
              Jump to latest
            </button>
          )}


          <div
            className="
              flex
              items-center
              gap-2
            "
          >

            {loading && (
              <span
                className="
                  h-2
                  w-2
                  animate-pulse
                  rounded-full
                  bg-teal-400
                "
              />
            )}

            <span
              className="
                text-xs
                text-teal-100
              "
            >
              {loading
                ? "RUNNING"
                : "IDLE"}
            </span>

          </div>

        </div>

      </div>


      {/* OUTPUT */}

      <div
        ref={consoleRef}
        onScroll={handleScroll}
        className="
          h-80
          overflow-y-auto
          p-4
          font-mono
          text-sm
          leading-6
          text-teal-300
        "
      >

        {logs.length === 0 && (
          <div className="text-slate-500">
            Waiting for Genetic Algorithm output...
          </div>
        )}


        {logs.map(
          (
            log,
            index
          ) => (
            <div
              key={`${index}-${log}`}
              className="
                whitespace-pre-wrap
                break-words
              "
            >
              {log === ""
                ? "\u00A0"
                : log}
            </div>
          )
        )}

        <div ref={bottomRef} />

      </div>

    </div>
  );
}