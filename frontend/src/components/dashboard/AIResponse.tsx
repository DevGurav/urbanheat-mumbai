"use client";


import ReactMarkdown from "react-markdown";



export default function AIResponse(
{
data
}:any
){


return (

<div className="
bg-slate-900
border
border-slate-800
rounded-3xl
p-8
">


<h2 className="
text-2xl
font-bold
mb-5
">

🤖 AI Heat Analysis

</h2>



<div className="
text-slate-300
leading-7
">

<ReactMarkdown>

{
data.ai_response
}

</ReactMarkdown>


</div>


</div>

)

}