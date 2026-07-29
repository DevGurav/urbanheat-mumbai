"use client";


import {
useState
} from "react";


import {
predictHeat
} from "../../services/api";



export default function ChatInput(
{
setData,
setLoading
}:any
){


const [location,setLocation]=
useState("");



async function search(){


if(!location)
return;



try{


setLoading(true);



const result =
await predictHeat(
location
);



console.log(result);



setData(result);



}

catch(error){

console.error(error);

alert(
"Backend connection failed"
);


}

finally{


setLoading(false);


}


}




return (

<div className="
flex
gap-4
">


<input

className="
flex-1
bg-slate-900
border
border-slate-700
rounded-xl
px-5
py-3
outline-none
"

placeholder="
Search Mumbai location...
"

value={location}

onChange={
e=>setLocation(e.target.value)
}

/>



<button

onClick={search}

className="
bg-orange-500
px-8
rounded-xl
font-semibold
hover:bg-orange-600
"

>

Analyze Heat

</button>


</div>

)

}