export default function StatCard(
{
title,
value
}:any
){


return (

<div className="
bg-slate-900
border
border-slate-800
rounded-2xl
p-6
shadow-lg
">


<p className="
text-slate-400
text-sm
">

{title}

</p>



<h2 className="
text-3xl
font-bold
mt-3
">

{value}

</h2>


</div>

)

}