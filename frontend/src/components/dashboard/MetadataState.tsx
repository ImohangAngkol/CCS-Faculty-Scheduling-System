export default function MetadataState({title, description, retry}: {
  title: string; description: string; retry?: () => void;
}) {
  return <div className="rounded-xl border border-slate-200 bg-white p-6" role={retry ? "alert" : "status"}>
    <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
    <p className="mt-2 text-sm text-slate-600">{description}</p>
    {retry && <button type="button" className="ccs-btn-secondary mt-4" onClick={retry}>Retry loading</button>}
  </div>;
}
