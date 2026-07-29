"use client";


import {
useState
} from "react";


import Sidebar from "../components/layout/SideBar";

import Header from "../components/layout/Header";


import Map from "../components/dashboard/Map";

import ChatInput from "../components/dashboard/ChatInput";

import StatCard from "../components/dashboard/StatCard";

import AIResponse from "../components/dashboard/AIResponse";



export default function Home(){


const [data,setData] =
useState<any>(null);



const [loading,setLoading] =
useState(false);



return (

<div className="
flex
min-h-screen
bg-slate-950
text-white
">


<Sidebar/>


<div className="
flex-1
">


<Header/>




<main className="
p-6
space-y-6
">



<ChatInput

setData={setData}

setLoading={setLoading}

/>





{
loading &&

<div className="
bg-slate-900
rounded-xl
p-5
animate-pulse
">

Analyzing satellite data...

</div>

}





<Map

prediction={data}

/>






<div className="
grid
grid-cols-1
md:grid-cols-4
gap-5
">


<StatCard

title="Land Surface Temperature"

value={

data

?

`${Number(data.predicted_LST).toFixed(2)} °C`

:

"--"

}

/>




<StatCard

title="Vegetation NDVI"

value={

data

?

Number(data.NDVI).toFixed(3)

:

"--"

}

/>





<StatCard

title="Built-up NDBI"

value={

data

?

Number(data.NDBI).toFixed(3)

:

"--"

}

/>




<StatCard

title="Heat Risk"

value={

data

?

data.risk

:

"--"

}

/>


</div>





{

data &&

<AIResponse

data={data}

/>

}



</main>



</div>


</div>

)

}