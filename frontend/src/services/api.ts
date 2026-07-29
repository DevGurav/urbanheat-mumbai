const API_URL = "http://127.0.0.1:8000";


export async function predictHeat(
    location:string
){

    const response = await fetch(
        `${API_URL}/heat/predict`,
        {
            method:"POST",

            headers:{
                "Content-Type":"application/json"
            },

            body:JSON.stringify({

                location,

                year:2026,

                month:12

            })

        }
    );


    if(!response.ok){

        throw new Error(
            "Heat prediction failed"
        );

    }


    return await response.json();

}