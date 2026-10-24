import {useEffect,useState} from "react";
import {Link} from "react-router-dom";
import {useAuth} from "../../context/AuthContext";
import {applicationAccess} from "../../api/scheduleApplications";
export default function ApplicationReviewLink(){
  const {user}=useAuth();const [verified,setVerified]=useState<string>();
  useEffect(()=>{const controller=new AbortController();if(user)void applicationAccess(controller.signal).then(()=>{if(!controller.signal.aborted)setVerified(user.id);}).catch(()=>{if(!controller.signal.aborted)setVerified(undefined);});return()=>controller.abort();},[user]);
  return user&&verified===user.id?<Link className="font-semibold text-teal-800 underline" to="/schedule-applications">Schedule applications</Link>:null;
}
