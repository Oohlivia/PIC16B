import pandas as pd
import numpy as np
import re

def trending_creators_by_country(youtube, country):
    '''
    Gets list of creator IDs of creators who had a video on selected country's trending page
    Returns more than 50 entries
    
    country: country of the trending page you want to access
        - To find code:
        - https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2 
        
    returns: list of channel IDs 
    
    '''
    channel_list = []
    request = youtube.videos().list(
        part="snippet,contentDetails",
        chart="mostPopular",
        regionCode=country,
        maxResults = 50
    )
    next_page = True
    pages = 0
    while next_page:
        response = request.execute()
        data = response["items"]
        
        for video in data:
            channel_id = video["snippet"]["channelId"] 
            if channel_id not in channel_list:
                channel_list.append(channel_id)
        if "nextPageToken" in response.keys():
            next_page = True
            request = youtube.videos().list(
                part="snippet, contentDetails",
                chart="mostPopular",
                regionCode=country,
                maxResults = 50,
                pageToken = response['nextPageToken']
            )
        else:
            next_page = False
    return channel_list


def channel_items(youtube,channel_id):
    '''
    Gets "items" from channel_id
    
    Contains playlist id, so you can access all a creator's video id with
    get_videoID_list
    '''
    request = youtube.channels().list(
        part = "snippet,contentDetails,statistics",
        id = channel_id
    )
    response= request.execute()
    
    # get only stats from"items" key
    return response['items']

    
def stats_loc_name(response_items):
    '''
    Uses response['items'] for a channel to pull out view count, subscriber count, video count, user name of channel, and location of creator
    
    channel_stats: return object from get_channel_stats
    '''
    viewCount = pd.to_numeric(response_items[0]["statistics"].get("viewCount",0))
    subscriberCount = pd.to_numeric(response_items[0]["statistics"].get("subscriberCount",0))
    videoCount = pd.to_numeric(response_items[0]["statistics"].get("videoCount",0))
    country = response_items[0]["snippet"].get("country",None)
    title = response_items[0]["snippet"].get("title",None)
    return title,country,viewCount,subscriberCount,videoCount


def get_1_channel_stats(youtube,channel_id):
    '''
    Gets list of items from youtube api for 1 channel
    '''
    request = youtube.channels().list(
        part = "snippet,contentDetails,statistics",
        id = channel_id
    )
    response= request.execute()
    
    # get only stats from"items" key
    return stats_loc_name(response['items'])

def get_1_channel_description(youtube,channel_id):
    '''
    Gets description from youtube api for 1 channel
    '''
    request = youtube.channels().list(
        part = "snippet,brandingSettings",
        id = channel_id
    )
    response= request.execute()
    
    # get only stats from"items" key
    
    #x = response['items'][0]
    x = response['items'][0]["snippet"].get("description",0)
    return x
        


def channels_stats(youtube,channel_ids):
    '''
    loops through list of channel ids to get channel stats and append to dataframe
    '''
    des = []
    all_data = []
    for channel_id in channel_ids:
        all_data.append(get_1_channel_stats(youtube,channel_id))
        des.append(get_1_channel_description(youtube,channel_id))
    df = pd.DataFrame(all_data, columns = ["title","country","viewCount","subscriberCount","videoCount"])
    df["description"] = des
    df["channel_id"] = channel_ids
    
    return df

def top_channels(df,column,percentile):
    '''
    filters dataframe of channel_stats to get top percentile based off a 
    column (viewCount,subscriberCount, or videoCount)
    
    df: channel_stats dataframe
    column: which column / stat you want to base percentile off of
    percentile: what percentile of creators, ex 95 is top 5% of creators
    '''
    num = np.percentile(pd.to_numeric(df[column]),percentile)
    return df[df[column] >= num].reset_index(drop=True)


def get_videoID_list(youtube, channel_id):
    '''
    Grabs unique ID for every video on a channel
    
    youtube: youtube API build()
   channel_id: unique ID for playlist of every video on channel
    
    Returns:list of unique ID of
    '''
    upload_id = channel_items(youtube,channel_id)[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    video_list = []
    request = youtube.playlistItems().list(
        part = "snippet,contentDetails",
        playlistId = upload_id,
        maxResults = 50 # most results you can get on one page from API is 50
    )
    next_page = True #when False means no more pages
    
    while next_page: #as long as next_page is true, it will keep searching for results
        response = request.execute()
        data = response['items']
        
        for video in data:
            video_id = video["contentDetails"]["videoId"] #for each video result, look into content details then in that get video ID
            if video_id not in video_list:
                video_list.append(video_id)
        if "nextPageToken" in response.keys(): #if in JSON theres a nextPageToken, it means there are more responses
            next_page = True
            request = youtube.playlistItems().list(
                part = "snippet,contentDetails",
                playlistId = upload_id,
                maxResults = 50,
                pageToken = response['nextPageToken']#gets next page of results           
            )
        else:
            next_page = False #exits the while loop
    return video_list



def get_video_details(youtube,video_list):
    '''
    Grabs data for all videos in a channel
    
    youtube: youtube API build()
    video_list: list containing all unique video IDs of data you want to grab
    
    returns: a list of dictionaries, each dictionary contains stats for a unique video
    
    '''
    stats_list = []
    all_stats = []
    #because YT only lets you grab 50 videos at a time
    #need to jump 0-49, 50-99 etc (count by 50)

    for i in range(0,len(video_list),50):
        request = youtube.videos().list(
            part = "snippet,contentDetails,status,statistics",
            id = video_list[i:i+50] #non inclusive, will grab 0-49
        )
        
        data = request.execute()
        
        for video in data["items"]:
            
            title = video["snippet"]['title']
            published = video['snippet']['publishedAt']
            description = video['snippet']['description']
            tags = video["snippet"].get('tags',[]) #how many tags video has bc 'tags' is a list
            postingDate = video['snippet'].get('publishedAt',None)
            description = video['snippet'].get('description',None)
            
            
            # .get ensures that if the info is unavailable (private etc), it won't throw an error, but put 0
            viewCount = video["statistics"].get("viewCount",0)
            likeCount = video["statistics"].get("likeCount",0)
            #dislike count is always private to public I think 
            dislikeCount = video["statistics"].get("dislikeCount","private")
            commentCount = video["statistics"].get("commentCount",0)
           
            
            made_for_kids = video['status'].get('madeForKids',None)
            
            #makes dictionary for each video with stas
            stats_dictionary = dict(title=title, 
                                    published=published,
                                    description = description,
                                    tags = tags,
                                    viewCount = viewCount,
                                    dislikeCount = dislikeCount,
                                    commentCount = commentCount,
                                    postingDate = postingDate,
                                    made_for_kids = made_for_kids
                                    
                                    
            )
            stats_list.append(stats_dictionary)
            
    return pd.DataFrame(stats_list)



def get_channel_id(video_id):
    """
    Given a video ID, return the ID of the channel it belongs to.
    
    @video_id: a string for video id
    """
    try:
        video_response = youtube.videos().list(id = video_id, part = 'snippet').execute()
        channel_id = video_response['items'][0]['snippet']['channelId']

        return channel_id

    except HttpError as error:
        return None

def get_channel_name(channel_id):
    """
    Given a channel ID, return the name of the channel.
    
    @channel_id: a string for channel_id
    """
    try:
        channel_response = youtube.channels().list(id = channel_id, part = 'snippet').execute()

        channel_name = channel_response['items'][0]['snippet']['title']

        return channel_name

    except HttpError as error:
        return None
    
