"use client";


import {
useEffect,
useRef
} from "react";


import maplibregl from "maplibre-gl";

import "maplibre-gl/dist/maplibre-gl.css";



export default function Map(
{
prediction
}:any
){


const mapContainer =
useRef<HTMLDivElement|null>(null);



useEffect(()=>{


if(!mapContainer.current)
return;



const map =
new maplibregl.Map({

container:
mapContainer.current,


style:
"https://demotiles.maplibre.org/style.json",


center:[

72.8777,

19.0760

],


zoom:10


});




if(prediction?.coordinates){



const marker =
new maplibregl.Marker({

color:"#ef4444"

});



marker

.setLngLat([

prediction.coordinates.longitude,

prediction.coordinates.latitude

])

.setPopup(

new maplibregl.Popup()

.setHTML(`

<div>

<h3>

🔥 ${prediction.location}

</h3>


<p>

Temperature:

<b>

${prediction.predicted_LST} °C

</b>

</p>


<p>

Risk:

<b>

${prediction.risk}

</b>

</p>


<p>

NDVI:

${Number(prediction.NDVI).toFixed(3)}

</p>


</div>

`)

)


.addTo(map);



map.flyTo({

center:[

prediction.coordinates.longitude,

prediction.coordinates.latitude

],

zoom:13

});


}




return ()=>{

map.remove();

};


},[prediction]);





return (

<div

ref={mapContainer}

className="
w-full
h-[500px]
rounded-3xl
overflow-hidden
border
border-slate-800
"

/>

)


}