import {
Map,
Brain,
Leaf,
BarChart3
} from "lucide-react";


export default function Sidebar(){


return (

<aside className="
w-64
bg-slate-900
border-r
border-slate-800
p-6
">


<h1 className="
text-xl
font-bold
mb-10
">

🔥 Urban Heat AI

</h1>



<div className="
space-y-6
text-slate-300
">


<div className="flex gap-3">

<Map/>

Dashboard

</div>


<div className="flex gap-3">

<Brain/>

AI Prediction

</div>


<div className="flex gap-3">

<Leaf/>

Vegetation

</div>


<div className="flex gap-3">

<BarChart3/>

Analytics

</div>


</div>


</aside>

)

}