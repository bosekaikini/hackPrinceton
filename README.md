# UrbanEyes
### Scaled Infrastructure Sustainability Project

## Inspiration
Urban Eyes was designed with our team's conscious vision to create a space that allows its citizens to thrive instead of stifling them, motivated by years of living in underfunded and impoverished communities here in the US and abroad. To this end, we leveraged the power of consumers to gather information related to urban sustainability on a transformative scale. We believe Urban Eyes can play an essential role in effectively organizing civil resources towards the sustainable betterment of communities for everyone.


## What it does
Data collection through wearable technology (prototype is camera on glasses) that uses computer vision and machine learning algorithms to categorize urban sustainability issues within the city (eg. structural faults, safety hazards, road maintenance, sewage management, excessive fumes, exposed waste, etc.). 


Location data for users was aggregated and analyzed through tailor-made algorithms to use pedestrian traffic as a metric in prioritizing issues detected across the user's choice of region.


These issues are then displayed with a radius based on their 'priority' level and their category. We added AI integration to explain each issue and add context based on its respective traffic data and priority level. We also used other APIs to webscrape for news about each incident and use those points as part of the analysis.


We ensure user count by modeling one part of our project, the app, off BeReal. The aspect of sampling pictures from wearable technology (of course, we took into account various privacy measures) offers a great incentive for people to use our app and therefore contribute to community betterment -- that incentive being human curiosity. BeReal was so successful because the appeal of seeing someone's authentic life is too tempting to resist. Each picture that is taken goes on the user's profile, and we foster this environment to reach maximum engagement towards our cause.


## How we built it


Our app is built in Android studio (so Kotlin, XML, Java, Gradle, etc.). Our machine learning model and some general algorithms are in Python. Our Raspberry Pi code to interact with our hardware (Intel RealSense D415 and air quality sensors) are in Python and Java. Our webpage has HTML and CSS code and most of it in Python.


Our basic flowchart has the website be an endpoint for analysis with data coming from the app. The app takes in some user information (account creation and location) and receives image data from the Raspberry Pi (which it feeds through our model before sending to the website). Our Raspberry Pi randomly samples images by sending instructions to the Camera and then sends each picture back to the app. 


The camera sits on a custom 3d-printed piece we designed to put onto glasses as our first draft of Urban Eyes' wearable technology component. 




## Challenges we ran into
All of us being primarily Computer Science students, the hardware track was a challenge we almost immediately thought we had gotten ourselves in over our heads in. 


From the get-go, there were problems. Parts wise, we started with the LogiTech Webcams but they couldn't meet our specifications, so we scouted around campus to find the Intel RealSense cameras that we stuck with. Similarly, we had to resort to finding our own Raspberry Pis since unfortunately there were too many challenges using the MLH provided ones with our computers. We also purchased SD cards to allow for better storage.


Truly, connecting the Raspberry Pi to the camera and connecting them all to the app and our website was the most challenging part of the process. Whole hours were spent, the team gathered around one computer, trying to make sense of the latest in a string of errors we could not comprehend in the least. 


Our real challenges, in our opinions, came in the experience of being software engineers. Dependency hell, framework compatibility, software mismatches and so, so many versions. Despite how tiring these are to deal with, we all found it fulfilling (to an extent) because it was truly an informative introduction to the software engineering experience.




## Accomplishments that we're proud of


We think many of the challenges we have here are also our biggest sources of pride. The hardware problems we had, for example, were certainly challenging and draining, but looking back we are all overwhelmingly happy to have stared down the Raspberry Pis and won. It's an earned victory in our eyes, just like every other time this weekend we've had to truly persevere through a task. Never regretted it once, though.


Our team relationships are also something we are very proud of. For a group formed exceedingly quickly with students across the country, we've gotten along so well we plan to continue going to hackathons for the foreseeable future. It's always nice to be a part of a capable, supportive group (and people you like).


Most of all we are proud of taking on an issue close to all of us personally and exploring a path that can truly have an impact.


## What we learned
We learn from our successes and even more from our failures, so we naturally learned a lot during this hackathon. 


The first thing (most) of us learned is that hardware can really be exciting. It has its moments. HackPrinceton was definitely unique in that we had never heard of other competitions actively encouraging incorporating hardware to the same extent before. 


Second, we were all truly surprised by just how powerful well-trained machine learning models can be. For all of us, it was nearly our first time building ML models. We were so new that when it took a whole night to upload to Google Cloud, we all honestly felt like something was seriously wrong. Our model had over ~82% accuracy. We incorporated Gemini support to further improve the model and reached 86% accuracy - for a quick image-classification problem with 10 different buckets it was amazing to see.




## What's next for Urban Eyes
Our team truly enjoyed finding this idea and learning just how well it connected with our backgrounds and experiences. We believe strongly in the need for Urban Eyes and have already planned on continuing work on it post HackPrinceton. We are sure, at least for the communities we grew up in, Urban Eyes could have a real impact. 


In terms of short-term improvements, more progress could definitely be made on the scope of our data collection measures. Image recognition offers up a grand selection of sustainability issues, but even then we miss some (like the lack of any very green spaces, or the possibility of pedestrian bottlenecks, etc.)


Over the long term, our goals are two-fold. First is to try and expand the use-cases for Urban Eyes, especially in our home communities, whether this be through more thorough model testing and evaluation or by talking to city officials, potential users, and other business owners to try and promote Urban Eyes potential. There's so much to be done, and we are truly grateful to have been able to discover a new calling at HackPrinceton.
