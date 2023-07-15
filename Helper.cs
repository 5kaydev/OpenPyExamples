using System.Text.RegularExpressions;
using System.Xml;
using Org.XmlUnit.Builder;
using Org.XmlUnit.Xpath;

namespace ConvertedTests.Helpers
{
    public class Helper
    {
        private static readonly Regex BlankRegex = new(@"^~blank.*$|^\s*$", RegexOptions.IgnoreCase);

        private static readonly Regex ContainsRegex = new(@"^~contains\((.*)\)$", RegexOptions.IgnoreCase);

        private static readonly Regex CountRegex = new(@"^~count\(\s*(\d.*)\s*\)$", RegexOptions.IgnoreCase);

        private static readonly Regex EmptyRegex = new(@"^empty.*$", RegexOptions.IgnoreCase);

        private static readonly Regex FlipRegex = new(@"^#flip#(.*)$", RegexOptions.IgnoreCase);

        private static readonly Regex NotBlankRegex = new(@"^~notblank.*$", RegexOptions.IgnoreCase);

        private static readonly Regex NotEmptyRegex = new(@"^notempty.*$", RegexOptions.IgnoreCase);

        private static readonly Regex NotEqualsRegex =
            new("^~notequals\\(\\s*\"(.*)\"\\s*\\)\\s*$", RegexOptions.IgnoreCase);

        private readonly XPathEngine _xpathEngine = new();

        private bool AttributeFilter(XmlAttribute attribute)
        {
            return !attribute.LocalName.Equals("nil");
        }

        private bool CompareXml(XmlNode controlXml, XmlNode testXml)
        {
            var diff = DiffBuilder.Compare(controlXml)
                .WithTest(testXml)
                .WithAttributeFilter(AttributeFilter)
                .CheckForSimilar()
                .IgnoreWhitespace()
                .Build();
            return !diff.HasDifferences();
        }

        private List<XmlNode> EvaluateXpath(string xml, string xpathSelector)
        {
            try
            {
                return _xpathEngine.SelectNodes(xpathSelector, Input.From(xml).Build()).ToList();
            }
            catch (Exception e)
            {
                Console.WriteLine(e);
                throw new Exception($"Exception while evaluating xpath expression {xpathSelector}\n on {xml}\n", e);
            }
        }

        private void FilterExtraXmlElements(List<XmlNode> responseNodes, List<XmlNode> valueNodes)
        {
            if (HasXmlElement(valueNodes[0].ChildNodes))
            {
                SortChildrenNodes(responseNodes[0]);
                SortChildrenNodes(valueNodes[0]);
                // Filtering response nodes if value contain at least one XmlElement child
                var toRemove = new List<XmlNode>();
                var responseChildren = responseNodes[0].ChildNodes;
                var responseIndex = 0;
                var valueChildren = valueNodes[0].ChildNodes;
                var valueIndex = 0;
                while (responseIndex < responseChildren.Count && valueIndex < valueChildren.Count)
                {
                    var responseNode = responseChildren.Item(responseIndex);
                    var valueNode = valueChildren[valueIndex];
                    if (responseNode.Name.Equals(valueNode.Name) && CompareXml(responseNode, valueNode))
                    {
                        responseIndex = responseIndex + 1;
                        valueIndex = valueIndex + 1;
                    }
                    else
                    {
                        toRemove.Add(responseNode);
                        responseIndex = responseIndex + 1;
                    }
                }
                while (responseIndex < responseChildren.Count)
                {
                    var responseNode = responseChildren.Item(responseIndex);
                    toRemove.Add(responseNode);
                    responseIndex = responseIndex + 1;
                }
                foreach (var node in toRemove)
                {
                    responseNodes[0].RemoveChild(node);
                }
            }
        }

        private bool HasXmlElement(XmlNodeList xmlNodeList)
        {
            for (var i = 0; i < xmlNodeList.Count; i++)
            {
                if (xmlNodeList.Item(i).GetType() == typeof(XmlElement))
                {
                    return true;
                }
            }
            return false;
        }

        private void SortChildrenNodes(XmlNode node)
        {
            var nodes = new List<ValueTuple<string, int, XmlNode>>();
            var childrenList = node.ChildNodes;
            for (var i = 0; i < childrenList.Count; i++)
            {
                var current = childrenList.Item(i);
                nodes.Add((current.Name, i, current));
            }
            nodes.Sort();
            node.RemoveAll();
            foreach (var tuple in nodes)
            {
                node.AppendChild(tuple.Item3);
            }
        }

        private string ValidateJsonBlank(Match match, string? responseJson, string expectedValue)
        {
            return string.IsNullOrWhiteSpace(responseJson)
                ? string.Empty
                : $"Result of json path expression should be blank but was\n{responseJson}";
        }

        private string ValidateJsonNotBlank(Match match, string? responseJson, string expectedValue)
        {
            return string.Empty.Equals(ValidateJsonBlank(match, responseJson, expectedValue))
                ? "Result of json path expression should not be blank"
                : string.Empty;
        }

        private string ValidateJsonEmpty(Match match, string? responseJson, string expectedValue)
        {
            return string.IsNullOrEmpty(responseJson)
                ? string.Empty
                : $"Result of json path expression should be empty but was\n{responseJson}";
        }

        private string ValidateJsonNotEmpty(Match match, string? responseJson, string expectedValue)
        {
            return string.Empty.Equals(ValidateJsonEmpty(match, responseJson, expectedValue))
                ? "Result of json path expression should not be empty"
                : string.Empty;
        }

        private string ValidateJsonResponseValidFlip(Match match, string? responseJson, string expectedValue)
        {
            var includedExpectedValue = match.Groups[1].Value;
            var message = ValidateJsonResponse(responseJson, includedExpectedValue);
            return string.Empty.Equals(message)
                ? $"Result of json path expression\n{responseJson}\nshould not match\n{includedExpectedValue}"
                : string.Empty;
        }

        private string ValidateJsonContains(Match match, string? responseJson, string expectedValue)
        {
            var containedValue = match.Groups[1].Value;
            return responseJson != null && responseJson.Contains(containedValue)
                ? string.Empty
                : $"Result of json path expression\n{responseJson}\ndoes not contain\n{containedValue}";
        }

        public string ValidateJsonResponse(string? responseJson, string expectedValue)
        {
            var assertionHandlers = new List<ValueTuple<Regex, Func<Match, string?, string, string>>>
            {
                (FlipRegex, ValidateJsonResponseValidFlip),
                (NotEqualsRegex, ValidateJsonResponseValidFlip),
                (EmptyRegex, ValidateJsonEmpty),
                (NotEmptyRegex, ValidateJsonNotEmpty),
                (BlankRegex, ValidateJsonBlank),
                (NotBlankRegex, ValidateJsonNotBlank),
                (ContainsRegex, ValidateJsonContains)
            };
            foreach (var assertionHandler in assertionHandlers)
            {
                var match = assertionHandler.Item1.Match(expectedValue);
                if (match.Success)
                {
                    return assertionHandler.Item2.Invoke(match, responseJson, expectedValue);
                }
            }
            // Regular assertion
            var equalValue = "null".Equals(expectedValue) ? null : expectedValue;
            return (equalValue == null && responseJson != null) ||
                   (equalValue != null && !equalValue.Equals(responseJson))
                ? $"Result of json path expression\n{responseJson}\nshould be equal to\n{expectedValue}"
                : string.Empty;
        }

        private bool XmlBlank(List<XmlNode> responseNodes)
        {
            return responseNodes.Count == 0 || string.IsNullOrWhiteSpace(responseNodes[0].InnerText.Trim());
        }

        private string ValidateXmlBlank(Match match, string responseXml, string xpathSelector, string expectedValue)
        {
            var responseNodes = EvaluateXpath(responseXml, xpathSelector);
            return XmlBlank(responseNodes)
                ? string.Empty
                : $"Result of xpath expression \n{xpathSelector}\nshould be blank but was\n{responseNodes[0].OuterXml}";
        }

        private string ValidateXmlNotBlank(Match match, string responseXml, string xpathSelector, string expectedValue)
        {
            var responseNodes = EvaluateXpath(responseXml, xpathSelector);
            return XmlBlank(responseNodes)
                ? $"Result of xpath expression \n{xpathSelector}\nshould not be blank"
                : string.Empty;
        }

        private bool XmlEmpty(List<XmlNode> responseNodes)
        {
            return responseNodes.Count == 0 || string.Empty.Equals(responseNodes[0].InnerText);
        }

        private string ValidateXmlEmpty(Match match, string responseXml, string xpathSelector, string expectedValue)
        {
            var responseNodes = EvaluateXpath(responseXml, xpathSelector);
            return XmlEmpty(responseNodes)
                ? string.Empty
                : $"Result of xpath expression \n{xpathSelector}\nshould be empty but was\n{responseNodes[0].OuterXml}";
        }

        private string ValidateXmlNotEmpty(Match match, string responseXml, string xpathSelector, string expectedValue)
        {
            var responseNodes = EvaluateXpath(responseXml, xpathSelector);
            return XmlEmpty(responseNodes)
                ? $"Result of xpath expression \n{xpathSelector}\nshould not be empty"
                : string.Empty;
        }

        private string ValidateXmlContains(Match match, string responseXml, string xpathSelector, string expectedValue)
        {
            var responseNodes = EvaluateXpath(responseXml, xpathSelector);
            if (responseNodes.Count == 0)
            {
                return $"Xpath expression {xpathSelector}\n did not retrieve any value\nbut expected {expectedValue}\n";
            }
            if (responseNodes[0].OuterXml == null)
            {
                return $"Xpath expression result is null\nbut expected {expectedValue}";
            }
            var expectedValues = match.Groups[1].Value.Split("|");
            var outerXml = responseNodes[0].OuterXml;
            return expectedValues.Any(value => outerXml.Contains(value))
                ? string.Empty
                : $"Xpath expression {xpathSelector}\n with result {outerXml}\ndid not contain any value from\n{expectedValue}";
        }

        private string ValidateXmlCount(Match match, string responseXml, string xpathSelector, string expectedValue)
        {
            int count;
            if (int.TryParse(match.Groups[1].Value, out count))
            {
                var responseNodes = EvaluateXpath(responseXml, xpathSelector);
                return count != responseNodes.Count
                    ? $"Xpath expression\n{xpathSelector}\nreturned a wrong number of results"
                    : string.Empty;
            }
            throw new Exception($"Invalid count in ~count expression {expectedValue}");
        }

        private string ValidateXmlResponseValidFlip(Match match, string responseXml, string xpathSelector,
            string expectedValue)
        {
            var includedExpectedValue = match.Groups[1].Value;
            var message = ValidateXmlResponse(responseXml, xpathSelector, includedExpectedValue);
            return string.Empty.Equals(message)
                ? $"Result of xpath expression \n{xpathSelector}\nshould not match\n{includedExpectedValue}"
                : string.Empty;
        }

        public string ValidateXmlResponse(string responseXml, string xpathSelector, string expectedValue)
        {
            var assertionHandlers = new List<ValueTuple<Regex, Func<Match, string, string, string, string>>>
            {
                (FlipRegex, ValidateXmlResponseValidFlip),
                (NotEqualsRegex, ValidateXmlResponseValidFlip),
                (EmptyRegex, ValidateXmlEmpty),
                (NotEmptyRegex, ValidateXmlNotEmpty),
                (BlankRegex, ValidateXmlBlank),
                (NotBlankRegex, ValidateXmlNotBlank),
                (ContainsRegex, ValidateXmlContains),
                (CountRegex, ValidateXmlCount)
            };
            foreach (var assertionHandler in assertionHandlers)
            {
                var match = assertionHandler.Item1.Match(expectedValue);
                if (match.Success)
                {
                    return assertionHandler.Item2.Invoke(match, responseXml, xpathSelector, expectedValue);
                }
            }
            var responseNodes = EvaluateXpath(responseXml, xpathSelector);
            if (responseNodes.Count == 0)
            {
                return $"Xpath expression {xpathSelector}\n did not retrieve any value\nbut expected {expectedValue}\n";
            }
            var parentNodeName = responseNodes[0].Name; // parent node name extracted from the response
            var expectedValueXml = expectedValue.StartsWith($"<{parentNodeName}>")
                ? expectedValue
                : $"<{parentNodeName}>{expectedValue}</{parentNodeName}>"; // expected value with the parent node as a string
            var valueNodes = EvaluateXpath(expectedValueXml, "/" + parentNodeName);
            var responseOuterXml = responseNodes[0].OuterXml;
            FilterExtraXmlElements(responseNodes, valueNodes);
            var diff = DiffBuilder.Compare(responseNodes[0])
                .WithTest(valueNodes[0])
                .WithAttributeFilter(AttributeFilter)
                .CheckForSimilar()
                .IgnoreWhitespace()
                .Build();
            return diff.HasDifferences()
                ? $"Xpath expression \n{xpathSelector}\nwith result\n{responseOuterXml}\ndoes not match value\n{expectedValue}\n in response \n{responseXml}\n and differences are \n{diff}\n"
                : string.Empty;
        }

        public string EvaluateXpathVariable(string responseXml, string xpathSelector)
        {
            var responseNodes = EvaluateXpath(responseXml, xpathSelector);
            if (responseNodes.Count == 0)
            {
                throw new Exception($"No value found for variable with Xpath expression{xpathSelector}");
            }
            if (HasXmlElement(responseNodes[0].ChildNodes))
            {
                return responseNodes[0].OuterXml;
            }
            return responseNodes[0].InnerText;
        }
    }
}