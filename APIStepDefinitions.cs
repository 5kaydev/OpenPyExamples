using System.Text.RegularExpressions;
using Newtonsoft.Json.Linq;
using NUnit.Framework;
using RestSharp;

namespace ConvertedTests.StepDefinitions;

[Binding]
public class APIStepDefinitions
{
    private static VariableStore variableStore = new VariableStore();
    private static AppConfig _appConfig = new AppConfig();
    private readonly string clientId = "489d90c0-8c9e-4f1e-a07a-1e46c510374c";
    private readonly string clientSecret = "elH4M66AfxgOfna9V7LV/KSFFRlke0SsdVfvY+98XOE=";
    private readonly string grantType = "client_credentials";

    private readonly string tokenLoginUrl =
        "https://login.microsoftonline.com/7389d8c0-3607-465c-a69f-7d4426502912/oauth2/v2.0/token";

    private ConvertedTests.AppProperties.AppEnvironment _appEnvironment;

    private Helper _helper;
    private IClient client;
    private string hostToken;
    private JArray jsnArrayResponse;
    private JObject jsnObjectResponse;
    private IRestResponse response;

    private string[] uriArray;

    public APIStepDefinitions(Helper helper)
    {
        _helper = helper;
        _appEnvironment = _appConfig.GetAppEnvironment("IN1");
    }


    [Given(@"I am a XMLWebservice client")]
    public void GivenIAmAXMLWebserviceClient()
    {
        client = ApiClient.GetInstance();
    }

    [When(@"I send a request to URL ""([^""]*)"" with request header ""([^""]*)"" and the following json body")]
    public void WhenISendAPOSTRequestToURLWithRequestHeaderAndTheFollowingJsonBody(string url, string headerToken,
        string multilineText)
    {
        uriArray = url.Split("]");
        var appHostId = uriArray[0].TrimStart('[');
        Console.WriteLine("**********************************************");
        //Console.WriteLine("appHostId " + appHostId);
        AppHost appHost = _appEnvironment.AppHosts.FirstOrDefault(a => a.Id == appHostId);
        APIHeader apiHeader = _appConfig.GetAPIHeader(headerToken, "json");
        var request = PrepareRequest(appHost, apiHeader, uriArray[1], "json");

        //replace all ~ items in the body 
        var substitutedString = variableStore.Substitute(multilineText);
        request.AddJsonBody(substitutedString);

        var client = new RestClient(appHost.Name);
        response = client.Execute(request);

        Assert.IsNotNull(response);
        Console.WriteLine("Response -->\t" + response.Content);
        jsnObjectResponse = null;
        jsnArrayResponse = null;
    }


    [Then(@"I validate that the Response Code should be (.*)")]
    public void ThenIValidateThatTheResponseCodeShouldBe(int p0)
    {
        Assert.AreEqual(p0, (int)response.StatusCode, "Expected status does not match.");
    }

    [Then(@"I validate that the json path expression ""(.*?)"" should be ""(.*?)""")]
    public void ThenIValidateThatTheJsonPathExpressionShouldBe(string jsonPathSelector, string expectedValue)
    {
        EnsureJsonResponseIsParsed();
        var actualValue = EvaluateJsonPath(jsonPathSelector);
        var expected = "null".Equals(expectedValue) ? null : expectedValue;
        Assert.AreEqual(expected, actualValue, "Expected value does not match the service response");
    }

    [Then(@"I store the value of the json path expression ""(.*?)"" in variable ""(.*?)""")]
    public void ThenIStoreTheValueOfTheJsonPathExpressionInVariable(string jsonPathSelector, string variableName)
    {
        EnsureJsonResponseIsParsed();
        var actualValue = EvaluateJsonPath(jsonPathSelector);
        variableStore.StoreVariable(variableName, actualValue);
    }

    [When(@"I send a request to URL ""([^""]*)"" with request header ""([^""]*)"" and the following xml body")]
    public void WhenISendAPOSTRequestToURLWithRequestHeaderAndTheFollowingXmlBody(string url, string headerToken,
        string multilineText)
    {
        uriArray = url.Split("]");
        var appHostId = uriArray[0].TrimStart('[');
        Console.WriteLine("**********************************************");
        //Console.WriteLine("appHostId " + appHostId); 
        AppHost appHost = _appEnvironment.AppHosts.FirstOrDefault(a => a.Id == appHostId);
        APIHeader apiHeader = _appConfig.GetAPIHeader(headerToken, "xml");
        var request = PrepareRequest(appHost, apiHeader, uriArray[1], "xml");

        //replace all ~ items in the body 
        request.AddParameter("application/xml", variableStore.Substitute(multilineText), ParameterType.RequestBody);

        var client = new RestClient(appHost.Name);
        response = client.Execute(request);

        Assert.IsNotNull(response);
        Console.WriteLine("Response -->\t" + response.Content);
    }

    /** Keep (.*?)
         * [Then(@"I validate that the xml path expression ""(.*?)"" should be ""(.*?)""")]
         */
    [Then(@"I validate that the xml path expression ""(.*?)"" should be ""(.*?)""")]
    public void ThenIValidateThatTheXmlPathExpressionShouldBe(string xpath, string value)
    {
        Console.WriteLine("xpath :" + xpath);
        Console.WriteLine("value :" + value);

        var substitutedValue = variableStore.Substitute(value);
        Console.WriteLine("xpath XML Substitute" + substitutedValue);
        _helper.AssertXmlResponseValid(response.Content, xpath, substitutedValue);
    }

    [Then(@"I store the value of the xml path expression ""(.*?)"" in variable ""(.*?)""")]
    public void ThenIStoreTheValueOfTheXmlPathExpressionInVariable(string xpath, string variableName)
    {
        var actualValue = _helper.EvaluateXpath(xpath, response.Content);
        variableStore.StoreVariable(variableName, actualValue);
    }

    public async Task<string> GenerateToken(string scope)
    {
        var handler = new HttpClientHandler();
        var client = new HttpClient(handler);
        var token = await client.SendAsync(new HttpRequestMessage(HttpMethod.Post, tokenLoginUrl)
        {
            Content = new FormUrlEncodedContent(new Dictionary<string, string>
            {
                { "grant_type", grantType },
                { "client_id", clientId },
                { "client_secret", clientSecret },
                { "scope", scope }
            })
        });

        token.EnsureSuccessStatusCode();

        var payload = JObject.Parse(await token.Content.ReadAsStringAsync());
        return payload.Value<string>("access_token");
    }

    private void EnsureJsonResponseIsParsed()
    {
        if (jsnObjectResponse == null && jsnArrayResponse == null)
        {
            if (response.Content.StartsWith('['))
            {
                jsnArrayResponse = JArray.Parse(response.Content);
            }
            else
            {
                jsnObjectResponse = JObject.Parse(response.Content);
            }
        }
    }

    private string EvaluateJsonPath(string jsonPathSelector)
    {
        if (jsnObjectResponse != null)
        {
            return (string)jsnObjectResponse.SelectToken(jsonPathSelector);
        }
        return (string)jsnArrayResponse.SelectToken(jsonPathSelector);
    }

    private RestRequest PrepareRequest(AppHost appHost, APIHeader apiHeader, string uri, string requestType)
    {
        var request = new RestRequest(uri);

        //Add header values
        var contentType = "application/" + requestType;
        request.AddHeader("Accept", contentType);
        request.AddHeader("Content-Type", contentType);
        request.AddHeader("sourcesystemidentifier", apiHeader.SourcesystemIdentifier);

        //Get AuthToken
        var authToken1 = "Bearer " + GenerateToken(appHost.Scope).Result;
        request.AddHeader("Authorization", authToken1);
        Console.WriteLine("authToken1 " + authToken1);
        Method method;
        if (Enum.TryParse<Method>(apiHeader.Verb, true, out method))
        {
            request.Method = method;
        }
        else
        {
            throw new Exception($"Unrecognized verb {apiHeader.Verb}");
        }
        return request;
    }

    public APIHeader GetAPIHeader(string headerToken, string requestType)
    {
        var regexp = new Regex(@"\(([^,]*),(.*)\)");
        var match = regexp.Match(headerToken);
        if (match.Success)
        {
            var accept = "application/" + requestType;
            var system = match.Groups[1].Value;
            var verb = match.Groups[2].Value;
            // TODO add the proper constructor parameters
            return new APIHeader();
        }
        if (hostMap.ContainsKey(headerToken))
        {
            return hostmap[headerToken];
        }
        throw new Exception($"APIHeader not found for request header {headerToken}");
    }
}