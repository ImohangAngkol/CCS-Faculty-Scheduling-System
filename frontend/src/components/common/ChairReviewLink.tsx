import {useEffect,useState} from "react";
import {Link} from "react-router-dom";
import {useAuth} from "../../context/AuthContext";
import {getChairAccess} from "../../api/chairReviews";

export default function ChairReviewLink(){
  const {user}=useAuth();const [verified,setVerified]=useState<string>();
  useEffect(()=>{const controller=new AbortController();if(user)void getChairAccess(controller.signal).then(()=>{if(!controller.signal.aborted)setVerified(user.id);}).catch(()=>setVerified(undefined));return()=>controller.abort();},[user]);
  return user&&verified===user.id?<Link className="font-semibold text-teal-800 underline" to="/chair/requests">Chair request reviews</Link>:null;
}
